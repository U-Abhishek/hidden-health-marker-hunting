"""
Environmental Conditions Module
--------------------------------
A pure-Python module that exposes a function to fetch environmental
conditions (air quality, weather, UV) for a given latitude, longitude,
and date. **No web server / FastAPI** — just call the function.

It aggregates:
  • Google Maps **Air Quality API** (current, forecast, or history)
  • **Open‑Meteo** (UV index, temperature, humidity, wind, etc.; free, no key)
  • **OpenUV** (optional; if OPENUV_API_KEY is set or passed)

Usage
-----
Async (recommended):
    from env_conditions_module import get_environment
    data = await get_environment(40.7128, -74.0060, date_str="2025-09-14")

Blocking helper (not from an event loop):
    from env_conditions_module import get_environment_blocking
    data = get_environment_blocking(40.7128, -74.0060, date_str="2025-09-14")

Environment variables (optional):
    # Google key: any of these names will be honored
    export GOOGLE_MAPS_API_KEY=YOUR_KEY
    # or
    export GOOGLE_MAPS_API=YOUR_KEY

    # Optional OpenUV key
    export OPENUV_API_KEY=YOUR_KEY

Notes
-----
• Google Air Quality "forecast:lookup" supports future up to ~96h; "history:lookup" supports past 30 days.
• Open‑Meteo returns local timezone data when timezone=auto. We also provide a local-noon hourly sample.
• If you pass both parameters and env vars for keys, **parameters win**.
"""
from __future__ import annotations

import os
import asyncio
from datetime import datetime, date as date_cls, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import httpx
from dateutil import tz

# ---- Constants ----
GOOGLE_AIR_BASE = "https://airquality.googleapis.com/v1"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
OPENUV_BASE = "https://api.openuv.io/api/v1/uv"

__all__ = ["get_environment", "get_environment_blocking"]

# ---- Utilities ----

def _get_google_key(env_override: Optional[str] = None) -> Optional[str]:
    if env_override and env_override.strip():
        return env_override.strip()
    for name in ("GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_API", "GMAPS_API_KEY", "MAPS_API_KEY"):
        v = os.getenv(name)
        if v and v.strip():
            return v.strip()
    return None


def _get_openuv_key(env_override: Optional[str] = None) -> Optional[str]:
    if env_override and env_override.strip():
        return env_override.strip()
    v = os.getenv("OPENUV_API_KEY")
    return v.strip() if v and v.strip() else None


def _parse_date(d: Optional[str], default_tz: str = "America/New_York") -> date_cls:
    if d is None:
        tzinfo = tz.gettz(os.environ.get("LOCAL_TZ", default_tz))
        return datetime.now(tzinfo).date()
    try:
        return datetime.fromisoformat(d).date()
    except Exception as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD. ({e})")


def _day_utc_window(day: date_cls) -> Tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _closest_hour_idx(times: list[str], target_dt: datetime, *, tzname: Optional[str] = None) -> int:
    """Return index of element in `times` (ISO8601 strings) closest to target_dt.
    Interprets naive times as being in `tzname` (if provided) or UTC.
    """
    tzinfo = tz.gettz(tzname) if tzname else timezone.utc
    target = target_dt.astimezone(tzinfo)
    diffs = []
    for i, t in enumerate(times):
        try:
            if t.endswith("Z"):
                ti = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(tzinfo)
            elif "+" in t[10:] or "-" in t[10:]:
                ti = datetime.fromisoformat(t).astimezone(tzinfo)
            else:
                ti = datetime.fromisoformat(t).replace(tzinfo=tzinfo)
        except Exception:
            continue
        diffs.append((abs((ti - target).total_seconds()), i))
    diffs.sort()
    return diffs[0][1] if diffs else 0


# ---- Fetchers ----
async def _fetch_google_air_quality(lat: float, lon: float, day: date_cls, *, client: httpx.AsyncClient, google_key: Optional[str]) -> Dict[str, Any]:
    key = _get_google_key(google_key)
    if not key:
        return {"error": "Missing Google API key"}

    start_utc, end_utc = _day_utc_window(day)
    now_utc = datetime.now(timezone.utc)

    payload_common = {
        "location": {"latitude": lat, "longitude": lon},
        "languageCode": "en",
        "universalAqi": True,
        "extraComputations": [
            "HEALTH_RECOMMENDATIONS",
            "DOMINANT_POLLUTANT_CONCENTRATION",
            "POLLUTANT_CONCENTRATION",
            "POLLUTANT_ADDITIONAL_INFO",
            "LOCAL_AQI",
        ],
    }

    headers = {
        "X-Goog-Api-Key": key,
        "Content-Type": "application/json",
    }

    out: Dict[str, Any] = {"used": []}

    async def _post(path: str, json_body: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
        url = f"{GOOGLE_AIR_BASE}/{path}"
        try:
            r = await client.post(url, headers=headers, json=json_body, timeout=timeout)
            if r.status_code >= 400:
                try:
                    err_json = r.json()
                except Exception:
                    err_json = {"text": r.text}
                return {"http_error": f"{r.status_code} {r.reason_phrase}", "body": err_json}
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # 1) current conditions (only if the requested day is today)
    if start_utc.date() == now_utc.date():
        out["current"] = await _post("currentConditions:lookup", payload_common, timeout=15)
        if "error" not in out["current"] and "http_error" not in out["current"]:
            out["used"].append("currentConditions:lookup")

    # 2) history (if within past 30 days)
    if end_utc <= now_utc and (now_utc - start_utc) <= timedelta(days=30):
        body = {
            **payload_common,
            "period": {
                "startTime": start_utc.isoformat().replace("+00:00", "Z"),
                "endTime": end_utc.isoformat().replace("+00:00", "Z"),
            },
            "pageSize": 200,
        }
        out["history"] = await _post("history:lookup", body)
        if "error" not in out["history"] and "http_error" not in out["history"]:
            out["used"].append("history:lookup")

    # 3) forecast (if today/future within 96h)
    if start_utc >= now_utc - timedelta(hours=1):
        start_dt = max(now_utc + timedelta(hours=1), start_utc)
        body = {**payload_common, "dateTime": start_dt.isoformat().replace("+00:00", "Z"), "pageSize": 200}
        out["forecast"] = await _post("forecast:lookup", body)
        if "error" not in out["forecast"] and "http_error" not in out["forecast"]:
            out["used"].append("forecast:lookup")

    return out


async def _fetch_open_meteo(lat: float, lon: float, day: date_cls, *, client: httpx.AsyncClient) -> Dict[str, Any]:
    today_utc = datetime.now(timezone.utc).date()
    base = OPEN_METEO_FORECAST if day >= today_utc else OPEN_METEO_HISTORICAL
    start = day.isoformat()
    end = day.isoformat()

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "apparent_temperature",
            "precipitation",
            "cloudcover",
            "wind_speed_10m",
            "uv_index",
            "uv_index_clear_sky",
        ]),
        "daily": ",".join([
            "uv_index_max",
            "uv_index_clear_sky_max",
        ]),
        "timezone": "auto",
        "start_date": start,
        "end_date": end,
    }
    try:
        r = await client.get(base, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e), "source": base, "params": params}

    # Representative hourly sample near local noon
    try:
        if "hourly" in data and "time" in data["hourly"]:
            times = data["hourly"]["time"]
            tzname = data.get("timezone", "UTC")
            local_noon = datetime.combine(day, datetime.min.time()).replace(tzinfo=tz.gettz(tzname)) + timedelta(hours=12)
            idx = _closest_hour_idx(times, local_noon, tzname=tzname)
            hourly_sample = {k: (v[idx] if isinstance(v, list) and len(v) > idx else None) for k, v in data["hourly"].items() if k != "time"}
        else:
            hourly_sample = None
    except Exception:
        hourly_sample = None

    return {
        "source": base,
        "params": params,
        "raw": data,
        "sample_at_local_noon": hourly_sample,
    }


async def _fetch_openuv(lat: float, lon: float, day: date_cls, *, client: httpx.AsyncClient, openuv_key: Optional[str]) -> Optional[Dict[str, Any]]:
    key = _get_openuv_key(openuv_key)
    if not key:
        return None

    local_tz = tz.gettz(os.environ.get("LOCAL_TZ", "America/New_York"))
    local_noon = datetime.combine(day, datetime.min.time()).replace(tzinfo=local_tz) + timedelta(hours=12)
    dt_param = local_noon.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    headers = {"x-access-token": key}
    try:
        r = await client.get(OPENUV_BASE, params={"lat": lat, "lng": lon, "dt": dt_param}, headers=headers, timeout=15)
        r.raise_for_status()
        uv_noon = r.json()
    except Exception as e:
        uv_noon = {"error": str(e)}

    uv_now = None
    if day == datetime.now(local_tz).date():
        try:
            r2 = await client.get(OPENUV_BASE, params={"lat": lat, "lng": lon}, headers=headers, timeout=15)
            r2.raise_for_status()
            uv_now = r2.json()
        except Exception as e:
            uv_now = {"error": str(e)}

    return {"noon": uv_noon, "now": uv_now}


# ---- Public API ----
async def get_environment(
    lat: float,
    lon: float,
    *,
    date_str: Optional[str] = None,
    google_key: Optional[str] = None,
    openuv_key: Optional[str] = None,
    default_tz: str = "America/New_York",
) -> Dict[str, Any]:
    """Fetch environmental conditions for (lat, lon) on a given date.

    Parameters
    ----------
    lat, lon : float
        Coordinates in decimal degrees.
    date_str : str, optional
        Date in YYYY-MM-DD. Defaults to "today" in default_tz.
    google_key : str, optional
        Google Maps Platform API key (Air Quality). If omitted, tries env vars.
    openuv_key : str, optional
        OpenUV API key. If omitted, tries env var OPENUV_API_KEY. Optional.
    default_tz : str
        Time zone used when interpreting "today".

    Returns
    -------
    dict
        A dictionary containing location, date, timezone, google_air_quality,
        weather, uv_extra, and sources.
    """
    d = _parse_date(date_str, default_tz)

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise ValueError("Invalid latitude/longitude range")

    async with httpx.AsyncClient() as client:
        g_task = asyncio.create_task(_fetch_google_air_quality(lat, lon, d, client=client, google_key=google_key))
        w_task = asyncio.create_task(_fetch_open_meteo(lat, lon, d, client=client))
        u_task = asyncio.create_task(_fetch_openuv(lat, lon, d, client=client, openuv_key=openuv_key))
        g, w, u = await asyncio.gather(g_task, w_task, u_task)

    tzname = (w.get("raw", {}).get("timezone") if isinstance(w, dict) else None) or default_tz

    return {
        "location": {"latitude": lat, "longitude": lon},
        "date": d.isoformat(),
        "timezone": tzname,
        "google_air_quality": g if isinstance(g, dict) else {"error": "google_air_quality fetch failed"},
        "weather": {k: v for k, v in w.items() if k in ("source", "params", "raw", "sample_at_local_noon")} if isinstance(w, dict) else {"error": "open-meteo fetch failed"},
        "uv_extra": u,
        "sources": {
            "google_air_quality": f"{GOOGLE_AIR_BASE}/(currentConditions|forecast|history)",
            "open_meteo": (OPEN_METEO_FORECAST if d >= datetime.now(timezone.utc).date() else OPEN_METEO_HISTORICAL),
            "openuv": OPENUV_BASE,
        },
    }


def get_environment_blocking(
    lat: float,
    lon: float,
    *,
    date_str: Optional[str] = None,
    google_key: Optional[str] = None,
    openuv_key: Optional[str] = None,
    default_tz: str = "America/New_York",
) -> Dict[str, Any]:
    """Blocking wrapper around :func:`get_environment`.
    Do not call this from within an existing asyncio event loop (e.g., Jupyter).
    """
    try:
        loop = asyncio.get_running_loop()
        # If we are already in an event loop, raise a clear error
        raise RuntimeError(
            "get_environment_blocking() called inside an existing event loop. "
            "Use: data = await get_environment(...)."
        )
    except RuntimeError:
        # No running loop -> safe to use asyncio.run
        return asyncio.run(
            get_environment(
                lat,
                lon,
                date_str=date_str,
                google_key=google_key,
                openuv_key=openuv_key,
                default_tz=default_tz,
            )
        )


# Optional: simple CLI for ad-hoc testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch environmental conditions (no server).")
    parser.add_argument("lat", type=float)
    parser.add_argument("lon", type=float)
    parser.add_argument("--date", dest="date_str", type=str, default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--google-key", dest="google_key", type=str, default=None)
    parser.add_argument("--openuv-key", dest="openuv_key", type=str, default=None)
    args = parser.parse_args()

    try:
        result = get_environment_blocking(
            args.lat,
            args.lon,
            date_str=args.date_str,
            google_key=args.google_key,
            openuv_key=args.openuv_key,
        )
        import json
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error: {exc}")
