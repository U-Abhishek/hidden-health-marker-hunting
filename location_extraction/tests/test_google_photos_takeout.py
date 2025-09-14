"""
Tests for Google Photos Takeout extractor.
"""

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from location_extraction.google_photos_takeout import (
    calculate_confidence,
    is_json_sidecar,
    parse_location,
    parse_sidecar_json,
    parse_takeout_zip_to_df,
    parse_timestamp,
    save_df,
)
from location_extraction.ingest_helpers import STANDARD_LOCATION_COLUMNS, to_standardized_df


class TestJSONSidecarDetection:
    """Test JSON sidecar file detection."""
    
    def test_detects_standard_json_sidecars(self):
        """Test detection of standard .json sidecar files."""
        assert is_json_sidecar("IMG_0001.jpg.json")
        assert is_json_sidecar("IMG_0001.jpeg.json")
        assert is_json_sidecar("IMG_0001.png.json")
        assert is_json_sidecar("IMG_0001.heic.json")
        assert is_json_sidecar("IMG_0001.mp4.json")
        assert is_json_sidecar("IMG_0001.mov.json")
    
    def test_detects_metadata_json_sidecars(self):
        """Test detection of .metadata.json sidecar files."""
        assert is_json_sidecar("IMG_0001.jpg.metadata.json")
        assert is_json_sidecar("IMG_0001.jpeg.metadata.json")
        assert is_json_sidecar("IMG_0001.png.metadata.json")
        assert is_json_sidecar("IMG_0001.heic.metadata.json")
        assert is_json_sidecar("IMG_0001.mp4.metadata.json")
        assert is_json_sidecar("IMG_0001.mov.metadata.json")
    
    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert is_json_sidecar("IMG_0001.JPG.JSON")
        assert is_json_sidecar("IMG_0001.JPEG.METADATA.JSON")
    
    def test_rejects_non_sidecar_files(self):
        """Test that non-sidecar files are rejected."""
        assert not is_json_sidecar("IMG_0001.jpg")
        assert not is_json_sidecar("IMG_0001.json")
        assert not is_json_sidecar("data.json")
        assert not is_json_sidecar("photo.txt")
        assert not is_json_sidecar("video.mp4")


class TestTimestampParsing:
    """Test timestamp extraction from JSON data."""
    
    def test_photo_taken_time_timestamp(self):
        """Test parsing from photoTakenTime.timestamp."""
        data = {
            "photoTakenTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00 UTC
            }
        }
        result = parse_timestamp(data)
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_creation_time_timestamp(self):
        """Test parsing from creationTime.timestamp."""
        data = {
            "creationTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00 UTC
            }
        }
        result = parse_timestamp(data)
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_creation_time_iso_string(self):
        """Test parsing from creationTime ISO string."""
        data = {
            "creationTime": "2021-01-01T00:00:00Z"
        }
        result = parse_timestamp(data)
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_creation_time_iso_with_offset(self):
        """Test parsing from creationTime ISO string with offset."""
        data = {
            "creationTime": "2021-01-01T00:00:00+00:00"
        }
        result = parse_timestamp(data)
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_priority_order(self):
        """Test that photoTakenTime takes priority over creationTime."""
        data = {
            "photoTakenTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00 UTC
            },
            "creationTime": {
                "timestamp": "1609545600"  # 2021-01-02 00:00:00 UTC
            }
        }
        result = parse_timestamp(data)
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected
    
    def test_no_timestamp(self):
        """Test handling of missing timestamp data."""
        data = {}
        result = parse_timestamp(data)
        assert result is None
    
    def test_invalid_timestamp(self):
        """Test handling of invalid timestamp data."""
        data = {
            "photoTakenTime": {
                "timestamp": "invalid"
            }
        }
        result = parse_timestamp(data)
        assert result is None


class TestLocationParsing:
    """Test location extraction from JSON data."""
    
    def test_geo_data_parsing(self):
        """Test parsing from geoData."""
        data = {
            "geoData": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracyMeters": 10.5,
                "geoIsEstimated": False
            }
        }
        lat, lon, accuracy, is_estimated = parse_location(data)
        assert lat == 40.7128
        assert lon == -74.0060
        assert accuracy == 10.5
        assert is_estimated is False
    
    def test_geo_data_exif_parsing(self):
        """Test parsing from geoDataExif."""
        data = {
            "geoDataExif": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracyMeters": 10.5,
                "geoIsEstimated": True
            }
        }
        lat, lon, accuracy, is_estimated = parse_location(data)
        assert lat == 40.7128
        assert lon == -74.0060
        assert accuracy == 10.5
        assert is_estimated is True
    
    def test_geo_data_priority(self):
        """Test that geoData takes priority over geoDataExif."""
        data = {
            "geoData": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracyMeters": 10.5,
                "geoIsEstimated": False
            },
            "geoDataExif": {
                "latitude": 50.0,
                "longitude": -80.0,
                "accuracyMeters": 20.0,
                "geoIsEstimated": True
            }
        }
        lat, lon, accuracy, is_estimated = parse_location(data)
        assert lat == 40.7128
        assert lon == -74.0060
        assert accuracy == 10.5
        assert is_estimated is False
    
    def test_no_location_data(self):
        """Test handling of missing location data."""
        data = {}
        lat, lon, accuracy, is_estimated = parse_location(data)
        assert lat is None
        assert lon is None
        assert accuracy is None
        assert is_estimated is False
    
    def test_string_coordinates(self):
        """Test conversion of string coordinates to float."""
        data = {
            "geoData": {
                "latitude": "40.7128",
                "longitude": "-74.0060",
                "accuracyMeters": "10.5"
            }
        }
        lat, lon, accuracy, is_estimated = parse_location(data)
        assert lat == 40.7128
        assert lon == -74.0060
        assert accuracy == 10.5


class TestConfidenceCalculation:
    """Test confidence score calculation."""
    
    def test_high_confidence(self):
        """Test high confidence for non-estimated GPS."""
        confidence = calculate_confidence(40.7128, -74.0060, False)
        assert confidence == 0.8
    
    def test_medium_confidence(self):
        """Test medium confidence for estimated GPS."""
        confidence = calculate_confidence(40.7128, -74.0060, True)
        assert confidence == 0.6
    
    def test_low_confidence_no_location(self):
        """Test low confidence for missing location."""
        confidence = calculate_confidence(None, None, False)
        assert confidence == 0.2


class TestSidecarJSONParsing:
    """Test complete JSON sidecar parsing."""
    
    def test_complete_sidecar_parsing(self):
        """Test parsing of complete sidecar JSON."""
        data = {
            "photoTakenTime": {
                "timestamp": "1609459200"
            },
            "geoData": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracyMeters": 10.5,
                "geoIsEstimated": False
            }
        }
        result = parse_sidecar_json(data, "user123")
        
        assert result is not None
        assert result["timestamp_utc"] == "2021-01-01T00:00:00+00:00"
        assert result["latitude"] == 40.7128
        assert result["longitude"] == -74.0060
        assert result["accuracy_m"] == 10.5
        assert result["source"] == "google_photos"
        assert result["provenance"] == "takeout-sidecar"
        assert result["confidence"] == 0.8
        assert result["user_id"] == "user123"
    
    def test_estimated_gps_parsing(self):
        """Test parsing with estimated GPS."""
        data = {
            "creationTime": {
                "timestamp": "1609459200"
            },
            "geoDataExif": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "geoIsEstimated": True
            }
        }
        result = parse_sidecar_json(data)
        
        assert result is not None
        assert result["confidence"] == 0.6
        assert result["accuracy_m"] is None
    
    def test_no_location_data(self):
        """Test parsing with no location data."""
        data = {
            "photoTakenTime": {
                "timestamp": "1609459200"
            }
        }
        result = parse_sidecar_json(data)
        assert result is None
    
    def test_no_timestamp(self):
        """Test parsing with no timestamp."""
        data = {
            "geoData": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        result = parse_sidecar_json(data)
        assert result is None


class TestZIPParsing:
    """Test ZIP file parsing functionality."""
    
    def create_test_zip(self, sidecar_data: list) -> Path:
        """Create a test ZIP file with sidecar JSON files."""
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "test_photos.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for i, data in enumerate(sidecar_data):
                filename = f"IMG_{i:04d}.jpg.json"
                json_str = json.dumps(data)
                zip_file.writestr(filename, json_str)
        
        return zip_path
    
    def test_parse_zip_with_gps_data(self):
        """Test parsing ZIP with GPS data."""
        sidecar_data = [
            {
                "photoTakenTime": {"timestamp": "1609459200"},
                "geoData": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "accuracyMeters": 10.5,
                    "geoIsEstimated": False
                }
            },
            {
                "creationTime": {"timestamp": "1609545600"},
                "geoDataExif": {
                    "latitude": 50.0,
                    "longitude": -80.0,
                    "geoIsEstimated": True
                }
            }
        ]
        
        zip_path = self.create_test_zip(sidecar_data)
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path), "user123")
            
            assert len(df) == 2
            assert list(df.columns) == STANDARD_LOCATION_COLUMNS
            assert df["user_id"].iloc[0] == "user123"
            assert df["confidence"].iloc[0] == 0.8  # Not estimated
            assert df["confidence"].iloc[1] == 0.6  # Estimated
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()
    
    def test_parse_zip_with_mixed_data(self):
        """Test parsing ZIP with mixed valid/invalid data."""
        sidecar_data = [
            {
                "photoTakenTime": {"timestamp": "1609459200"},
                "geoData": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            },
            {
                "photoTakenTime": {"timestamp": "1609545600"}
                # No location data
            },
            {
                "geoData": {
                    "latitude": 50.0,
                    "longitude": -80.0
                }
                # No timestamp
            }
        ]
        
        zip_path = self.create_test_zip(sidecar_data)
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path))
            
            # Should only have 1 valid record
            assert len(df) == 1
            assert df["latitude"].iloc[0] == 40.7128
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()
    
    def test_parse_empty_zip(self):
        """Test parsing empty ZIP file."""
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "empty.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            pass  # Empty ZIP
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path))
            assert len(df) == 0
            assert list(df.columns) == STANDARD_LOCATION_COLUMNS
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()
    
    def test_parse_zip_with_metadata_files(self):
        """Test parsing ZIP with .metadata.json files."""
        sidecar_data = [
            {
                "photoTakenTime": {"timestamp": "1609459200"},
                "geoData": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            }
        ]
        
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "test_photos.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            # Add both .json and .metadata.json files
            json_str = json.dumps(sidecar_data[0])
            zip_file.writestr("IMG_0001.jpg.json", json_str)
            zip_file.writestr("IMG_0002.jpg.metadata.json", json_str)
            zip_file.writestr("other_file.txt", "not a sidecar")
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path))
            
            # Should find both sidecar files
            assert len(df) == 2
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()


class TestDataFrameSaving:
    """Test DataFrame saving functionality."""
    
    def test_save_csv(self):
        """Test saving DataFrame to CSV."""
        df = pd.DataFrame({
            "timestamp_utc": ["2021-01-01T00:00:00+00:00"],
            "latitude": [40.7128],
            "longitude": [-74.0060],
            "accuracy_m": [10.5],
            "source": ["google_photos"],
            "provenance": ["takeout-sidecar"],
            "confidence": [0.8],
            "user_id": ["user123"]
        })
        
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            save_df(df, str(temp_path))
            assert temp_path.exists()
            
            # Verify content
            loaded_df = pd.read_csv(temp_path)
            assert len(loaded_df) == 1
            assert loaded_df["latitude"].iloc[0] == 40.7128
        finally:
            temp_path.unlink()
    
    def test_save_parquet(self):
        """Test saving DataFrame to Parquet."""
        df = pd.DataFrame({
            "timestamp_utc": ["2021-01-01T00:00:00+00:00"],
            "latitude": [40.7128],
            "longitude": [-74.0060],
            "accuracy_m": [10.5],
            "source": ["google_photos"],
            "provenance": ["takeout-sidecar"],
            "confidence": [0.8],
            "user_id": ["user123"]
        })
        
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            save_df(df, str(temp_path))
            assert temp_path.exists()
            
            # Verify content
            loaded_df = pd.read_parquet(temp_path)
            assert len(loaded_df) == 1
            assert loaded_df["latitude"].iloc[0] == 40.7128
        finally:
            temp_path.unlink()
    
    def test_save_invalid_format(self):
        """Test saving with invalid file format."""
        df = pd.DataFrame({"test": [1]})
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                save_df(df, str(temp_path))
        finally:
            temp_path.unlink()


class TestSchemaCompatibility:
    """Test compatibility with standardized schema."""
    
    def test_schema_columns_match(self):
        """Test that output columns match the standardized schema."""
        from location_extraction.ingest_helpers import STANDARD_LOCATION_COLUMNS
        
        # Create test data
        sidecar_data = [
            {
                "photoTakenTime": {"timestamp": "1609459200"},
                "geoData": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            }
        ]
        
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "test_photos.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            json_str = json.dumps(sidecar_data[0])
            zip_file.writestr("IMG_0001.jpg.json", json_str)
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path))
            assert list(df.columns) == STANDARD_LOCATION_COLUMNS
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()
    
    def test_data_types_compatible(self):
        """Test that data types are compatible with metrics extraction."""
        sidecar_data = [
            {
                "photoTakenTime": {"timestamp": "1609459200"},
                "geoData": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "accuracyMeters": 10.5
                }
            }
        ]
        
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "test_photos.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            json_str = json.dumps(sidecar_data[0])
            zip_file.writestr("IMG_0001.jpg.json", json_str)
        
        try:
            df = parse_takeout_zip_to_df(str(zip_path))
            
            # Check that coordinates are numeric
            assert pd.api.types.is_numeric_dtype(df["latitude"])
            assert pd.api.types.is_numeric_dtype(df["longitude"])
            
            # Check that timestamp is datetime
            assert pd.api.types.is_datetime64_any_dtype(df["timestamp_utc"])
            
            # Check coordinate ranges
            assert (df["latitude"] >= -90).all()
            assert (df["latitude"] <= 90).all()
            assert (df["longitude"] >= -180).all()
            assert (df["longitude"] <= 180).all()
        finally:
            zip_path.unlink()
            zip_path.parent.rmdir()
