"""Integration tests for GET /weather/state endpoint."""

import time


class TestGetWeatherState:
    """Tests for GET /weather/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /weather/state returns response with correct structure.
        
        Per WeatherStateResponse model, response should include:
        - modality_type: "weather"
        - last_updated: ISO format timestamp
        - update_count: integer
        - locations: dict mapping location keys to weather data
        - location_count: number of tracked locations
        """
        client, engine = client_with_engine
        
        response = client.get("/weather/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "modality_type" in data
        assert data["modality_type"] == "weather"
        assert "last_updated" in data
        assert "update_count" in data
        assert isinstance(data["update_count"], int)
        assert "locations" in data
        assert isinstance(data["locations"], dict)
        assert "location_count" in data
        assert isinstance(data["location_count"], int)

    def test_returns_empty_locations_initially(self, client_with_engine):
        """Test that state has no locations when no weather data has been added.
        
        Note: Unlike location modality, weather fixture creates an empty state
        with no pre-populated locations.
        """
        client, engine = client_with_engine
        
        response = client.get("/weather/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Initially no locations tracked
        assert data["locations"] == {}
        assert data["location_count"] == 0
        assert data["update_count"] == 0

    def test_reflects_weather_update(self, client_with_engine):
        """Test that state shows updated weather after update action."""
        client, engine = client_with_engine
        
        # Create a weather update
        now = int(time.time())
        update_response = client.post(
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
                        "temp": 295.15,  # ~72°F
                        "feels_like": 295.15,
                        "pressure": 1013,
                        "humidity": 55,
                        "dew_point": 285.15,
                        "uvi": 5.0,
                        "clouds": 20,
                        "visibility": 10000,
                        "wind_speed": 3.5,
                        "wind_deg": 180,
                        "weather": [
                            {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                        ],
                    },
                },
            },
        )
        assert update_response.status_code == 200
        
        # Check state reflects update
        state_response = client.get("/weather/state")
        assert state_response.status_code == 200
        
        data = state_response.json()
        assert data["update_count"] == 1
        assert data["location_count"] == 1
        
        # Location key is normalized (rounded to 2 decimal places)
        assert "40.71,-74.01" in data["locations"]

    def test_includes_all_weather_components(self, client_with_engine):
        """Test that state includes current, hourly, and daily forecasts when provided."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Create weather update with all components
        client.post(
            "/weather/update",
            json={
                "latitude": 37.7749,
                "longitude": -122.4194,
                "report": {
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "timezone": "America/Los_Angeles",
                    "timezone_offset": -28800,
                    "current": {
                        "dt": now,
                        "sunrise": now - 3600,
                        "sunset": now + 36000,
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
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                    "hourly": [
                        {
                            "dt": now + 3600,
                            "temp": 290.15,
                            "feels_like": 290.15,
                            "pressure": 1013,
                            "humidity": 55,
                            "dew_point": 281.15,
                            "uvi": 4.0,
                            "clouds": 15,
                            "visibility": 10000,
                            "wind_speed": 4.0,
                            "wind_deg": 200,
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
                            "temp": {"day": 290.15, "min": 285.15, "max": 295.15, "night": 283.15, "eve": 288.15, "morn": 286.15},
                            "feels_like": {"day": 290.15, "night": 283.15, "eve": 288.15, "morn": 286.15},
                            "pressure": 1013,
                            "humidity": 60,
                            "dew_point": 280.15,
                            "wind_speed": 3.5,
                            "wind_deg": 180,
                            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                            "clouds": 20,
                            "pop": 0.0,
                            "uvi": 5.0,
                        }
                    ],
                },
            },
        )
        
        state_response = client.get("/weather/state")
        data = state_response.json()
        
        location_key = "37.77,-122.42"
        assert location_key in data["locations"]
        
        location = data["locations"][location_key]
        report = location["current_report"]
        
        assert "current" in report
        assert report["current"] is not None
        assert "hourly" in report
        assert report["hourly"] is not None
        assert len(report["hourly"]) == 1
        assert "daily" in report
        assert report["daily"] is not None
        assert len(report["daily"]) == 1

    def test_includes_weather_alerts(self, client_with_engine):
        """Test that state includes weather alerts when present."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Create weather update with alerts
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
                        "pressure": 1008,
                        "humidity": 80,
                        "dew_point": 290.15,
                        "uvi": 1.0,
                        "clouds": 90,
                        "visibility": 5000,
                        "wind_speed": 15.0,
                        "wind_deg": 90,
                        "weather": [{"id": 202, "main": "Thunderstorm", "description": "thunderstorm with heavy rain", "icon": "11d"}],
                    },
                    "alerts": [
                        {
                            "sender_name": "NWS",
                            "event": "Severe Thunderstorm Warning",
                            "start": now,
                            "end": now + 7200,
                            "description": "Severe thunderstorms expected in the area.",
                            "tags": ["thunderstorm", "severe"],
                        }
                    ],
                },
            },
        )
        
        state_response = client.get("/weather/state")
        data = state_response.json()
        
        location_key = "40.71,-74.01"
        assert location_key in data["locations"]
        
        location = data["locations"][location_key]
        report = location["current_report"]
        
        assert "alerts" in report
        assert report["alerts"] is not None
        assert len(report["alerts"]) == 1
        assert report["alerts"][0]["event"] == "Severe Thunderstorm Warning"

    def test_tracks_multiple_locations(self, client_with_engine):
        """Test that state can track weather for multiple locations simultaneously."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Add weather for multiple locations
        locations = [
            (40.7128, -74.0060, "America/New_York"),  # NYC
            (34.0522, -118.2437, "America/Los_Angeles"),  # LA
            (51.5074, -0.1278, "Europe/London"),  # London
        ]
        
        for lat, lon, tz in locations:
            client.post(
                "/weather/update",
                json={
                    "latitude": lat,
                    "longitude": lon,
                    "report": {
                        "lat": lat,
                        "lon": lon,
                        "timezone": tz,
                        "timezone_offset": 0,
                        "current": {
                            "dt": now,
                            "sunrise": now - 3600,
                            "sunset": now + 36000,
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
                            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                        },
                    },
                },
            )
        
        state_response = client.get("/weather/state")
        data = state_response.json()
        
        assert data["location_count"] == 3
        assert data["update_count"] == 3
        assert len(data["locations"]) == 3

    def test_last_updated_changes_with_updates(self, client_with_engine):
        """Test that last_updated timestamp changes when weather is updated."""
        client, engine = client_with_engine
        
        # Get initial state
        initial_response = client.get("/weather/state")
        initial_time = initial_response.json()["last_updated"]
        
        # Advance simulator time
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Update weather
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
        
        # Get updated state
        updated_response = client.get("/weather/state")
        updated_time = updated_response.json()["last_updated"]
        
        # last_updated should have changed
        assert updated_time != initial_time
