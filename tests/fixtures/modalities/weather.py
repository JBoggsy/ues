"""Fixtures for Weather modality."""

from datetime import datetime, timezone

from models.modalities.weather_input import (
    WeatherInput,
    WeatherReport,
    CurrentWeather,
    WeatherCondition,
)
from models.modalities.weather_state import WeatherState


def create_weather_input(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    report: WeatherReport | None = None,
    timestamp: datetime | None = None,
    **kwargs,
) -> WeatherInput:
    """Create a WeatherInput with sensible defaults.

    Args:
        latitude: Location latitude (default: San Francisco).
        longitude: Location longitude (default: San Francisco).
        report: Complete weather report (default: simple clear weather).
        timestamp: When weather data was recorded (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        WeatherInput instance ready for testing.
    """
    if report is None:
        # Create simple default weather report
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        report = WeatherReport(
            lat=latitude,
            lon=longitude,
            timezone="America/Los_Angeles",
            timezone_offset=-28800,
            current=CurrentWeather(
                dt=now_timestamp,
                sunrise=now_timestamp - 3600,
                sunset=now_timestamp + 36000,
                temp=288.15,  # 15°C / 59°F
                feels_like=288.15,
                pressure=1013,
                humidity=60,
                dew_point=280.15,
                uvi=3.0,
                clouds=20,
                visibility=10000,
                wind_speed=3.5,
                wind_deg=180,
                weather=[
                    WeatherCondition(
                        id=800,
                        main="Clear",
                        description="clear sky",
                        icon="01d",
                    )
                ],
            ),
        )
    
    return WeatherInput(
        latitude=latitude,
        longitude=longitude,
        report=report,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs,
    )


def create_weather_state(
    last_updated: datetime | None = None,
    **kwargs,
) -> WeatherState:
    """Create a WeatherState with sensible defaults.

    Args:
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        WeatherState instance ready for testing.
    """
    return WeatherState(
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built weather examples
CLEAR_WEATHER = create_weather_input()

RAINY_WEATHER = create_weather_input(
    report=WeatherReport(
        lat=37.7749,
        lon=-122.4194,
        timezone="America/Los_Angeles",
        timezone_offset=-28800,
        current=CurrentWeather(
            dt=int(datetime.now(timezone.utc).timestamp()),
            sunrise=int(datetime.now(timezone.utc).timestamp()) - 3600,
            sunset=int(datetime.now(timezone.utc).timestamp()) + 36000,
            temp=283.15,  # 10°C / 50°F
            feels_like=281.15,
            pressure=1008,
            humidity=85,
            dew_point=280.15,
            uvi=1.0,
            clouds=90,
            visibility=8000,
            wind_speed=8.0,
            wind_deg=270,
            weather=[
                WeatherCondition(
                    id=500,
                    main="Rain",
                    description="light rain",
                    icon="10d",
                )
            ],
        ),
    )
)

SNOWY_WEATHER = create_weather_input(
    report=WeatherReport(
        lat=40.7128,
        lon=-74.0060,
        timezone="America/New_York",
        timezone_offset=-18000,
        current=CurrentWeather(
            dt=int(datetime.now(timezone.utc).timestamp()),
            sunrise=int(datetime.now(timezone.utc).timestamp()) - 3600,
            sunset=int(datetime.now(timezone.utc).timestamp()) + 32400,
            temp=271.15,  # -2°C / 28°F
            feels_like=268.15,
            pressure=1015,
            humidity=75,
            dew_point=268.15,
            uvi=0.5,
            clouds=100,
            visibility=5000,
            wind_speed=5.0,
            wind_deg=0,
            weather=[
                WeatherCondition(
                    id=600,
                    main="Snow",
                    description="light snow",
                    icon="13d",
                )
            ],
        ),
    )
)

HOT_WEATHER = create_weather_input(
    report=WeatherReport(
        lat=33.4484,
        lon=-112.0740,
        timezone="America/Phoenix",
        timezone_offset=-25200,
        current=CurrentWeather(
            dt=int(datetime.now(timezone.utc).timestamp()),
            sunrise=int(datetime.now(timezone.utc).timestamp()) - 3600,
            sunset=int(datetime.now(timezone.utc).timestamp()) + 43200,
            temp=313.15,  # 40°C / 104°F
            feels_like=316.15,
            pressure=1010,
            humidity=20,
            dew_point=285.15,
            uvi=11.0,
            clouds=0,
            visibility=10000,
            wind_speed=2.0,
            wind_deg=135,
            weather=[
                WeatherCondition(
                    id=800,
                    main="Clear",
                    description="clear sky",
                    icon="01d",
                )
            ],
        ),
    )
)


# State examples
EMPTY_WEATHER_STATE = create_weather_state()


# Invalid examples for validation testing
INVALID_WEATHER_INPUTS = {
    "latitude_too_high": {
        "latitude": 100.0,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc),
    },
    "longitude_too_low": {
        "latitude": 37.7749,
        "longitude": -200.0,
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
WEATHER_JSON_EXAMPLES = {
    "clear": {
        "modality_type": "weather",
        "timestamp": "2025-01-15T10:30:00Z",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "report": {
            "lat": 37.7749,
            "lon": -122.4194,
            "timezone": "America/Los_Angeles",
            "timezone_offset": -28800,
            "current": {
                "dt": 1705318200,
                "sunrise": 1705314600,
                "sunset": 1705350600,
                "temp": 288.15,
                "feels_like": 288.15,
                "pressure": 1013,
                "humidity": 60,
                "dew_point": 280.15,
                "uvi": 3.0,
                "clouds": 20,
                "visibility": 10000,
                "wind_speed": 3.5,
                "wind_deg": 180,
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
            },
        },
    },
}
