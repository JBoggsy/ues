"""Integration tests for POST /weather/query endpoint."""

import time


class TestPostWeatherQuery:
    """Tests for POST /weather/query endpoint."""

    def test_query_returns_correct_structure(self, client_with_engine):
        """Test that query returns response with correct structure.
        
        Per WeatherQueryResponse model, response should include:
        - reports: list of WeatherReport objects
        - count: number of reports returned
        - total_count: total matching reports
        - error: optional error message
        """
        client, engine = client_with_engine
        
        # First add some weather data
        now = int(time.time())
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        response = client.post("/weather/query", json={"lat": 40.7128, "lon": -74.0060})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "reports" in data
        assert isinstance(data["reports"], list)
        assert "count" in data
        assert isinstance(data["count"], int)
        assert "total_count" in data

    def test_query_requires_coordinates(self, client_with_engine):
        """Test that query requires lat/lon parameters."""
        client, engine = client_with_engine
        
        # Missing both lat and lon
        response = client.post("/weather/query", json={})
        assert response.status_code == 422
        
        # Missing lon
        response = client.post("/weather/query", json={"lat": 40.7128})
        assert response.status_code == 422
        
        # Missing lat
        response = client.post("/weather/query", json={"lon": -74.0060})
        assert response.status_code == 422

    def test_query_with_coordinates_succeeds(self, client_with_engine):
        """Test querying weather for specific coordinates returns matching data."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather data
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Query for that location
        response = client.post("/weather/query", json={"lat": 40.7128, "lon": -74.0060})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert len(data["reports"]) == 1
        
        report = data["reports"][0]
        assert abs(report["lat"] - 40.7128) < 0.02  # Allow for rounding
        assert abs(report["lon"] - (-74.0060)) < 0.02

    def test_query_with_units_metric(self, client_with_engine):
        """Test querying weather with metric units converts temperatures.
        
        Per docs: metric units = temperature in Celsius, wind speed in m/s
        Standard units store temp in Kelvin (295.15K = 22°C)
        """
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather data with standard units (Kelvin)
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,  # 22°C in Kelvin
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Query with metric units
        response = client.post(
            "/weather/query",
            json={"lat": 40.7128, "lon": -74.0060, "units": "metric"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        report = data["reports"][0]
        
        # Temperature should be converted from Kelvin to Celsius
        # 295.15K - 273.15 = 22°C
        assert abs(report["current"]["temp"] - 22.0) < 0.1

    def test_query_with_units_imperial(self, client_with_engine):
        """Test querying weather with imperial units converts temperatures and wind speed.
        
        Per docs: imperial units = temperature in Fahrenheit, wind speed in mph
        Standard units store temp in Kelvin (295.15K = 71.6°F)
        """
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather data with standard units (Kelvin)
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,  # ~71.6°F in Kelvin
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 10.0,  # m/s -> ~22.4 mph
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Query with imperial units
        response = client.post(
            "/weather/query",
            json={"lat": 40.7128, "lon": -74.0060, "units": "imperial"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        report = data["reports"][0]
        
        # Temperature should be converted from Kelvin to Fahrenheit
        # (295.15K - 273.15) * 9/5 + 32 = 71.6°F
        assert abs(report["current"]["temp"] - 71.6) < 0.5
        
        # Wind speed should be converted from m/s to mph
        # 10 m/s * 2.23694 = ~22.4 mph
        assert abs(report["current"]["wind_speed"] - 22.4) < 0.5

    def test_query_with_exclude_current(self, client_with_engine):
        """Test excluding current weather from response."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather with all components
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                    "hourly": [
                        {
                            "dt": now + 3600,
                            "temp": 296.15,
                            "feels_like": 296.15,
                            "pressure": 1013,
                            "humidity": 50,
                            "dew_point": 284.15,
                            "uvi": 6.0,
                            "clouds": 10,
                            "visibility": 10000,
                            "wind_speed": 4.0,
                            "wind_deg": 190,
                            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                            "pop": 0.0,
                        }
                    ],
                },
            },
        )
        
        # Query excluding current
        response = client.post(
            "/weather/query",
            json={"lat": 40.7128, "lon": -74.0060, "exclude": ["current"]},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        report = data["reports"][0]
        
        # Current should be None/excluded
        assert report["current"] is None
        # Hourly should still be present
        assert report["hourly"] is not None

    def test_query_with_exclude_multiple(self, client_with_engine):
        """Test excluding multiple weather components (hourly, daily, alerts)."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather with all components
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                    "hourly": [
                        {
                            "dt": now + 3600,
                            "temp": 296.15,
                            "feels_like": 296.15,
                            "pressure": 1013,
                            "humidity": 50,
                            "dew_point": 284.15,
                            "uvi": 6.0,
                            "clouds": 10,
                            "visibility": 10000,
                            "wind_speed": 4.0,
                            "wind_deg": 190,
                            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                            "pop": 0.0,
                        }
                    ],
                    "daily": [
                        {
                            "dt": now,
                            "sunrise": now - 3600,
                            "sunset": now + 36000,
                            "moonrise": now + 43200,
                            "moonset": now - 21600,
                            "moon_phase": 0.5,
                            "temp": {"day": 296.15, "min": 290.15, "max": 300.15, "night": 288.15, "eve": 294.15, "morn": 291.15},
                            "feels_like": {"day": 296.15, "night": 288.15, "eve": 294.15, "morn": 291.15},
                            "pressure": 1013,
                            "humidity": 55,
                            "dew_point": 285.15,
                            "wind_speed": 3.5,
                            "wind_deg": 180,
                            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                            "clouds": 20,
                            "pop": 0.0,
                            "uvi": 5.0,
                        }
                    ],
                    "alerts": [
                        {
                            "sender_name": "NWS",
                            "event": "Heat Advisory",
                            "start": now,
                            "end": now + 7200,
                            "description": "Hot weather expected.",
                            "tags": ["heat"],
                        }
                    ],
                },
            },
        )
        
        # Query excluding hourly, daily, and alerts
        response = client.post(
            "/weather/query",
            json={"lat": 40.7128, "lon": -74.0060, "exclude": ["hourly", "daily", "alerts"]},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        report = data["reports"][0]
        
        # Current should still be present
        assert report["current"] is not None
        # Excluded sections should be None
        assert report["hourly"] is None
        assert report["daily"] is None
        assert report["alerts"] is None

    def test_query_with_time_range(self, client_with_engine):
        """Test querying historical weather data for time range using from_time parameter."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add initial weather data
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Get the time after first update
        time_response = client.get("/simulator/time")
        from_time = time_response.json()["current_time"]
        
        # Advance time and add another update
        client.post("/simulator/time/advance", json={"seconds": 3600})
        
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now + 3600,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 298.15,  # Warmer
                        "feels_like": 298.15,
                        "pressure": 1012,
                        "humidity": 50,
                        "dew_point": 286.15,
                        "uvi": 6.0,
                        "clouds": 10,
                        "visibility": 10000,
                        "wind_speed": 4.0,
                        "wind_deg": 200,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Query with from_time to get historical data
        # Note: from_time should be Unix timestamp (seconds since epoch)
        from datetime import datetime
        from_timestamp = int(datetime.fromisoformat(from_time.replace("Z", "+00:00")).timestamp())
        
        response = client.post(
            "/weather/query",
            json={"lat": 40.7128, "lon": -74.0060, "from_time": from_timestamp},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include both current and historical reports
        assert data["count"] >= 1

    def test_empty_results_when_no_data_available(self, client_with_engine):
        """Test handling when no weather data available for queried location."""
        client, engine = client_with_engine
        
        # Query for a location with no weather data
        response = client.post("/weather/query", json={"lat": 0.0, "lon": 0.0})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 0
        assert data["reports"] == []

    def test_query_nearby_coordinates_uses_same_location_key(self, client_with_engine):
        """Test that nearby coordinates within rounding precision map to the same location.
        
        Per design, coordinates are rounded to 2 decimal places (~0.01 degrees, ~1km precision)
        to prevent duplicate nearby locations.
        
        Example: 40.7128 rounds to 40.71, and 40.714 also rounds to 40.71, so they match.
        """
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather at a specific location (40.7128 rounds to 40.71)
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
                        "temp": 295.15,
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                },
            },
        )
        
        # Query with slightly different coordinates that round to the same key
        # 40.7128 -> 40.71, and 40.714 -> 40.71 (both round to same key)
        # -74.0060 -> -74.01, and -74.009 -> -74.01 (both round to same key)
        response = client.post(
            "/weather/query",
            json={"lat": 40.714, "lon": -74.009},  # Within rounding precision
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find the same location due to coordinate rounding
        assert data["count"] == 1
