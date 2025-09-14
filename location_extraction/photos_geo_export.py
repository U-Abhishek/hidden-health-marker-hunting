#!/usr/bin/env python3
"""
photos_geo_export.py — Export timestamp + latitude + longitude from Apple Photos to CSV.

REQUIREMENTS (install first):
    • macOS with an Apple Photos library.
    • Python 3.8+.
    • The osxphotos package (which reads Photos’ local database; no uploads involved)
       Depending on how you have setup pip on your system, this will look something like:
          pip install --upgrade osxphotos
       or, if you use pipx:
          pipx install osxphotos

PERMISSIONS:
    • On macOS, you may need to grant your terminal/Python "Full Disk Access":
      System Settings → Privacy & Security → Full Disk Access → (add Terminal, iTerm, or your IDE).

WHAT THIS DOES:
    • Reads your *local* Photos library (default system library) via osxphotos.
    • Writes a CSV with columns: timestamp, latitude, longitude
      - timestamp format: ISO‑8601 with milliseconds and offset, e.g. 2009-11-20T13:57:14.072-05:00
      - includes only items that have GPS coordinates
      - sorted chronologically

USAGE:
    # default output to ~/Desktop/photos_geo.csv
    python3 photos_geo_export.py

    # custom output path
    python3 photos_geo_export.py -o /path/to/output.csv

NOTES:
    • If a photo/video has no GPS data, it's skipped.
    • If some timestamps lack time zone info (rare), the script falls back to the
      time zone recorded with the photo (if available) or your current local time zone.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from osxphotos import PhotosDB
except ModuleNotFoundError:
    sys.stderr.write(
        "Error: 'osxphotos' is not installed.\n"
        "Install it with:  pip install --upgrade osxphotos\n"
        "Or, if you use pipx:  pipx install osxphotos\n"
    )
    sys.exit(1)


def _ensure_tzaware(dt: datetime, tzoffset_seconds: int | None) -> datetime:
    """
    Ensure the datetime is timezone-aware so we can emit an ISO-8601 string
    with an explicit offset (e.g., ...-05:00). osxphotos typically returns
    aware datetimes already; this is a safe fallback.
    """
    if dt.tzinfo is not None:
        return dt
    # Prefer per-asset offset if osxphotos provides it
    if isinstance(tzoffset_seconds, int):
        return dt.replace(tzinfo=timezone(timedelta(seconds=tzoffset_seconds)))
    # Fallback to the current local timezone
    local_tz = datetime.now().astimezone().tzinfo
    return dt.replace(tzinfo=local_tz)


def export_csv(output_path: Path) -> int:
    """
    Export a CSV with columns: timestamp, latitude, longitude.
    Returns the number of rows written.
    """
    try:
        db = PhotosDB()  # opens the default Photos library
    except Exception as e:  # pragma: no cover
        sys.stderr.write(
            "Failed to open the Photos library. If you're on macOS Ventura or later, "
            "make sure your terminal/IDE has Full Disk Access.\n"
            f"Underlying error: {e}\n"
        )
        sys.exit(2)

    rows: list[tuple[datetime, float, float]] = []

    # Iterate every asset; include any with GPS (photo or video).
    for p in db.photos():
        lat, lon = getattr(p, "latitude", None), getattr(p, "longitude", None)
        if lat is None or lon is None:
            continue
        dt: datetime = getattr(p, "date", None)  # creation date/time
        if dt is None:
            continue
        # Some versions expose a tz offset in seconds; use it if available.
        tzoffset_seconds = getattr(p, "tzoffset", None)
        dt = _ensure_tzaware(dt, tzoffset_seconds)
        rows.append((dt, float(lat), float(lon)))

    # Sort chronologically
    rows.sort(key=lambda r: r[0])

    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "latitude", "longitude"])
        for dt, lat, lon in rows:
            # Exactly like 2009-11-20T13:57:14.072-05:00
            ts = dt.isoformat(timespec="milliseconds")
            w.writerow([ts, f"{lat:.6f}", f"{lon:.6f}"])
            count += 1

    return count


def main() -> None:
    default_out = Path.home() / "Desktop" / "photos_geo.csv"
    parser = argparse.ArgumentParser(
        description="Export ISO-8601 timestamps (with milliseconds) and GPS coordinates from Apple Photos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help="Path to the CSV to write",
    )
    args = parser.parse_args()

    written = export_csv(args.output)
    print(f"Wrote {written} rows to {args.output}")


if __name__ == "__main__":
    main()
