"""Unit tests for WeatherInput.

This test suite covers:
1. General ModalityInput behavior (applicable to all modalities)
2. Weather-specific input validation and features
"""

from datetime import datetime, timezone

import pytest

from models.modalities.weather_input import (
    CurrentWeather,
    WeatherCondition,
    WeatherInput,
    WeatherReport,
)
from tests.fixtures.modalities.weather import (
    CLEAR_WEATHER,
    HOT_WEATHER,
    RAINY_WEATHER,
    SNOWY_WEATHER,
    create_weather_input,
)


class TestWeatherInputInstantiation:
    """Test WeatherInput instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityInput subclasses should test instantiation,
    default values, and proper inheritance from ModalityInput.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating WeatherInput with only required fields."""
        now = datetime.now(timezone.utc)
        timestamp_unix = int(now.timestamp())
        
        report = WeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
            current=CurrentWeather(
                dt=timestamp_unix,
                sunrise=timestamp_unix - 3600,
                sunset=timestamp_unix + 36000,
                temp=293.15,
                feels_like=293.15,
                pressure=1013,
                humidity=65,
                dew_point=285.15,
                uvi=5.0,
                clouds=30,
                visibility=10000,
                wind_speed=4.0,
                wind_deg=200,
                weather=[WeatherCondition(id=800, main="Clear", description="clear sky", icon="01d")],
            ),
        )
        
        weather = WeatherInput(
            latitude=40.7128,
            longitude=-74.0060,
            report=report,
            timestamp=now,
        )
        
        assert weather.latitude == 40.7128
        assert weather.longitude == -74.0060
        assert weather.report == report
        assert weather.timestamp == now

    def test_instantiation_with_all_fields(self):
        """Test creating WeatherInput with all fields."""
        now = datetime.now(timezone.utc)
        report = create_weather_input().report
        
        weather = WeatherInput(
            latitude=51.5074,
            longitude=-0.1278,
            report=report,
            timestamp=now,
        )
        
        assert weather.latitude == 51.5074
        assert weather.longitude == -0.1278
        assert weather.timestamp == now

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        weather = create_weather_input()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            weather.modality_type = "other"

    def test_instantiation_default_modality_type(self):
        """Test that modality_type defaults to 'weather'."""
        weather = create_weather_input()
        assert weather.modality_type == "weather"


class TestWeatherInputValidation:
    """Test WeatherInput validation logic.
    
    WEATHER-SPECIFIC: Test latitude/longitude range validation and weather report structure.
    """

    def test_validate_latitude_in_range(self):
        """Test that valid latitudes are accepted."""
        valid_lats = [-90.0, -45.0, 0.0, 45.0, 90.0]
        for lat in valid_lats:
            weather = create_weather_input(latitude=lat)
            assert weather.latitude == lat

    def test_validate_latitude_too_low(self):
        """Test that latitudes below -90 are rejected."""
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            create_weather_input(latitude=-90.1)

    def test_validate_latitude_too_high(self):
        """Test that latitudes above 90 are rejected."""
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            create_weather_input(latitude=90.1)

    def test_validate_longitude_in_range(self):
        """Test that valid longitudes are accepted."""
        valid_lons = [-180.0, -90.0, 0.0, 90.0, 180.0]
        for lon in valid_lons:
            weather = create_weather_input(longitude=lon)
            assert weather.longitude == lon

    def test_validate_longitude_too_low(self):
        """Test that longitudes below -180 are rejected."""
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            create_weather_input(longitude=-180.1)

    def test_validate_longitude_too_high(self):
        """Test that longitudes above 180 are rejected."""
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            create_weather_input(longitude=180.1)

    def test_validate_weather_report_structure(self):
        """Test that weather report contains required fields."""
        weather = create_weather_input()
        report = weather.report
        
        assert hasattr(report, 'lat')
        assert hasattr(report, 'lon')
        assert hasattr(report, 'timezone')
        assert hasattr(report, 'current')
        assert isinstance(report.current, CurrentWeather)

    def test_validate_current_weather_has_temperature(self):
        """Test that current weather includes temperature data."""
        weather = create_weather_input()
        current = weather.report.current
        
        assert hasattr(current, 'temp')
        assert hasattr(current, 'feels_like')
        assert isinstance(current.temp, (int, float))
        assert isinstance(current.feels_like, (int, float))

    def test_validate_current_weather_has_conditions(self):
        """Test that current weather includes weather conditions."""
        weather = create_weather_input()
        current = weather.report.current
        
        assert hasattr(current, 'weather')
        assert isinstance(current.weather, list)
        assert len(current.weather) > 0
        assert all(isinstance(c, WeatherCondition) for c in current.weather)


class TestWeatherInputAbstractMethods:
    """Test WeatherInput implementation of ModalityInput abstract methods.
    
    GENERAL PATTERN: All ModalityInput subclasses must implement these methods.
    """

    def test_validate_input_succeeds(self):
        """Test that validate_input passes for valid weather data."""
        weather = create_weather_input()
        weather.validate_input()  # Should not raise

    def test_get_affected_entities_returns_location(self):
        """Test that get_affected_entities returns location coordinates."""
        weather = create_weather_input(latitude=40.7128, longitude=-74.0060)
        entities = weather.get_affected_entities()
        
        # Format is "weather_location:lat,lon" with 4 decimal places
        assert any("40.7128" in entity and "-74.0060" in entity for entity in entities)

    def test_get_summary_includes_location(self):
        """Test that summary includes location information."""
        weather = create_weather_input(latitude=37.7749, longitude=-122.4194)
        summary = weather.get_summary()
        
        # Summary includes coordinates with 4 decimal places
        assert "37.7749" in summary
        assert "-122.4194" in summary

    def test_get_summary_includes_temperature(self):
        """Test that summary includes temperature information."""
        weather = CLEAR_WEATHER
        summary = weather.get_summary()
        
        # Summary should include temperature in some form
        assert "temp" in summary.lower() or "°" in summary or "weather" in summary.lower()

    def test_get_summary_includes_conditions(self):
        """Test that summary includes weather condition description."""
        weather = RAINY_WEATHER
        summary = weather.get_summary()
        
        # Should mention rain in some form
        assert any(word in summary.lower() for word in ["rain", "rainy", "precipitation"])

    def test_should_merge_with_returns_false(self):
        """Test that should_merge_with returns False for weather inputs."""
        weather1 = create_weather_input()
        weather2 = create_weather_input()
        
        assert weather1.should_merge_with(weather2) is False

    def test_should_merge_with_different_type(self):
        """Test merge behavior with different modality types."""
        weather = create_weather_input()
        
        class OtherInput:
            modality_type = "other"
        
        assert weather.should_merge_with(OtherInput()) is False


class TestWeatherInputSerialization:
    """Test WeatherInput serialization and deserialization.
    
    GENERAL PATTERN: All ModalityInput subclasses should support Pydantic
    serialization via model_dump() and model_validate().
    """

    def test_serialization_to_dict(self):
        """Test serializing WeatherInput to dictionary."""
        weather = create_weather_input(
            latitude=48.8566,
            longitude=2.3522,
        )
        
        data = weather.model_dump()
        
        assert data["modality_type"] == "weather"
        assert data["latitude"] == 48.8566
        assert data["longitude"] == 2.3522
        assert "report" in data
        assert "timestamp" in data

    def test_deserialization_from_dict(self):
        """Test deserializing WeatherInput from dictionary."""
        original = create_weather_input(latitude=35.6762, longitude=139.6503)
        data = original.model_dump()
        
        restored = WeatherInput.model_validate(data)
        
        assert restored.modality_type == original.modality_type
        assert restored.latitude == original.latitude
        assert restored.longitude == original.longitude
        assert restored.report.lat == original.report.lat
        assert restored.report.lon == original.report.lon

    def test_serialization_roundtrip(self):
        """Test complete serialization/deserialization roundtrip."""
        original = RAINY_WEATHER
        
        data = original.model_dump()
        restored = WeatherInput.model_validate(data)
        
        assert restored.latitude == original.latitude
        assert restored.longitude == original.longitude
        assert restored.report.current.temp == original.report.current.temp
        assert len(restored.report.current.weather) == len(original.report.current.weather)
        assert restored.report.current.weather[0].main == original.report.current.weather[0].main

    def test_serialization_preserves_weather_conditions(self):
        """Test that weather conditions are preserved during serialization."""
        weather = SNOWY_WEATHER
        
        data = weather.model_dump()
        restored = WeatherInput.model_validate(data)
        
        assert len(restored.report.current.weather) > 0
        assert restored.report.current.weather[0].id == weather.report.current.weather[0].id
        assert restored.report.current.weather[0].main == weather.report.current.weather[0].main
        assert restored.report.current.weather[0].description == weather.report.current.weather[0].description


class TestWeatherInputFixtures:
    """Test pre-built weather input fixtures.
    
    GENERAL PATTERN: Verify that test fixtures are properly constructed.
    """

    def test_clear_weather_fixture(self):
        """Test CLEAR_WEATHER fixture is valid."""
        assert CLEAR_WEATHER.modality_type == "weather"
        assert CLEAR_WEATHER.report.current.weather[0].main == "Clear"

    def test_rainy_weather_fixture(self):
        """Test RAINY_WEATHER fixture is valid."""
        assert RAINY_WEATHER.modality_type == "weather"
        assert "rain" in RAINY_WEATHER.report.current.weather[0].main.lower()

    def test_snowy_weather_fixture(self):
        """Test SNOWY_WEATHER fixture is valid."""
        assert SNOWY_WEATHER.modality_type == "weather"
        assert "snow" in SNOWY_WEATHER.report.current.weather[0].main.lower()

    def test_hot_weather_fixture(self):
        """Test HOT_WEATHER fixture is valid."""
        assert HOT_WEATHER.modality_type == "weather"
        # Hot weather should have higher temperature (>30°C = >303.15K)
        assert HOT_WEATHER.report.current.temp > 303.15


class TestWeatherInputEdgeCases:
    """Test edge cases and boundary conditions.
    
    WEATHER-SPECIFIC: Test extreme weather conditions and coordinate boundaries.
    """

    def test_extreme_cold_temperature(self):
        """Test weather input with extreme cold temperature."""
        now = datetime.now(timezone.utc)
        timestamp_unix = int(now.timestamp())
        
        report = WeatherReport(
            lat=90.0,  # North Pole
            lon=0.0,
            timezone="UTC",
            timezone_offset=0,
            current=CurrentWeather(
                dt=timestamp_unix,
                sunrise=timestamp_unix - 86400,  # Polar night
                sunset=timestamp_unix + 86400,
                temp=233.15,  # -40°C
                feels_like=223.15,  # -50°C with wind chill
                pressure=1025,
                humidity=80,
                dew_point=228.15,
                uvi=0.0,
                clouds=100,
                visibility=1000,
                wind_speed=15.0,
                wind_deg=0,
                weather=[WeatherCondition(id=600, main="Snow", description="heavy snow", icon="13d")],
            ),
        )
        
        weather = WeatherInput(
            latitude=90.0,
            longitude=0.0,
            report=report,
            timestamp=now,
        )
        
        assert weather.report.current.temp < 273.15  # Below freezing

    def test_extreme_hot_temperature(self):
        """Test weather input with extreme hot temperature."""
        weather = HOT_WEATHER
        assert weather.report.current.temp > 310.15  # >37°C

    def test_multiple_weather_conditions(self):
        """Test weather input with multiple simultaneous conditions."""
        now = datetime.now(timezone.utc)
        timestamp_unix = int(now.timestamp())
        
        report = WeatherReport(
            lat=0.0,
            lon=0.0,
            timezone="UTC",
            timezone_offset=0,
            current=CurrentWeather(
                dt=timestamp_unix,
                sunrise=timestamp_unix - 21600,
                sunset=timestamp_unix + 21600,
                temp=298.15,
                feels_like=301.15,
                pressure=1008,
                humidity=85,
                dew_point=295.15,
                uvi=8.0,
                clouds=75,
                visibility=8000,
                wind_speed=8.0,
                wind_deg=135,
                weather=[
                    WeatherCondition(id=500, main="Rain", description="light rain", icon="10d"),
                    WeatherCondition(id=801, main="Clouds", description="few clouds", icon="02d"),
                ],
            ),
        )
        
        weather = WeatherInput(
            latitude=0.0,
            longitude=0.0,
            report=report,
            timestamp=now,
        )
        
        assert len(weather.report.current.weather) == 2

    def test_zero_visibility_conditions(self):
        """Test weather with zero visibility (heavy fog/storm)."""
        now = datetime.now(timezone.utc)
        timestamp_unix = int(now.timestamp())
        
        report = WeatherReport(
            lat=51.5074,
            lon=-0.1278,
            timezone="Europe/London",
            timezone_offset=0,
            current=CurrentWeather(
                dt=timestamp_unix,
                sunrise=timestamp_unix - 14400,
                sunset=timestamp_unix + 28800,
                temp=280.15,
                feels_like=278.15,
                pressure=1010,
                humidity=95,
                dew_point=279.15,
                uvi=0.0,
                clouds=100,
                visibility=0,  # Zero visibility
                wind_speed=2.0,
                wind_deg=90,
                weather=[WeatherCondition(id=741, main="Fog", description="fog", icon="50d")],
            ),
        )
        
        weather = WeatherInput(
            latitude=51.5074,
            longitude=-0.1278,
            report=report,
            timestamp=now,
        )
        
        assert weather.report.current.visibility == 0

    def test_international_date_line_crossing(self):
        """Test weather at extreme longitudes near date line."""
        weather_west = create_weather_input(latitude=0.0, longitude=-179.9)
        weather_east = create_weather_input(latitude=0.0, longitude=179.9)
        
        assert weather_west.longitude < 0
        assert weather_east.longitude > 0
        assert abs(weather_west.longitude - weather_east.longitude) > 359
