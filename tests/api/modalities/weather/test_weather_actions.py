"""Integration tests for weather action endpoints."""

import time


class TestPostWeatherUpdate:
    """Tests for POST /weather/update endpoint."""

    def test_update_returns_correct_structure(self, client_with_engine):
        """Test that update response has correct structure.
        
        Per ModalityActionResponse model, response should include:
        - event_id: str
        - scheduled_time: datetime
        - status: str
        - message: str
        - modality: str
        """
        client, engine = client_with_engine
        
        now = int(time.time())
        
        response = client.post(
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
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_id" in data
        assert "scheduled_time" in data
        assert "status" in data
        assert "message" in data
        assert "modality" in data
        assert data["modality"] == "weather"

    def test_update_with_current_conditions(self, client_with_engine):
        """Test updating weather with current conditions data."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        response = client.post(
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
                        "feels_like": 293.15,
                        "pressure": 1015,
                        "humidity": 60,
                        "dew_point": 287.15,
                        "uvi": 4.5,
                        "clouds": 25,
                        "visibility": 10000,
                        "wind_speed": 5.5,
                        "wind_deg": 220,
                        "wind_gust": 8.0,
                        "weather": [
                            {"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}
                        ],
                    },
                },
            },
        )
        
        assert response.status_code == 200
        
        # Verify weather state was updated
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        assert state["update_count"] == 1
        assert len(state["locations"]) == 1
        
        # Get the location data
        loc_key = list(state["locations"].keys())[0]
        loc_data = state["locations"][loc_key]
        
        assert loc_data["current_report"]["current"]["temp"] == 295.15
        assert loc_data["current_report"]["current"]["humidity"] == 60
        assert loc_data["current_report"]["current"]["wind_speed"] == 5.5

    def test_update_with_hourly_forecast(self, client_with_engine):
        """Test updating weather with hourly forecast data."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        hourly_data = []
        for i in range(6):  # 6 hours of forecast
            hourly_data.append({
                "dt": now + (i + 1) * 3600,
                "temp": 295.15 + i,
                "feels_like": 294.15 + i,
                "pressure": 1013,
                "humidity": 55 - i,
                "dew_point": 285.15,
                "uvi": 5.0 - i * 0.5 if i < 4 else 0.0,
                "clouds": 20 + i * 5,
                "visibility": 10000,
                "wind_speed": 3.5 + i * 0.5,
                "wind_deg": 180,
                "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                "pop": 0.0 + i * 0.05,
            })
        
        response = client.post(
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
                    "hourly": hourly_data,
                },
            },
        )
        
        assert response.status_code == 200
        
        # Verify hourly data in state
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        loc_key = list(state["locations"].keys())[0]
        loc_data = state["locations"][loc_key]
        
        assert loc_data["current_report"]["hourly"] is not None
        assert len(loc_data["current_report"]["hourly"]) == 6

    def test_update_with_daily_forecast(self, client_with_engine):
        """Test updating weather with daily forecast data."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        daily_data = []
        for i in range(3):  # 3 days of forecast
            daily_data.append({
                "dt": now + i * 86400,
                "sunrise": now + i * 86400 - 3600,
                "sunset": now + i * 86400 + 36000,
                "moonrise": now + i * 86400 + 43200,
                "moonset": now + i * 86400 - 21600,
                "moon_phase": 0.5 + i * 0.1,
                "temp": {
                    "day": 296.15 + i,
                    "min": 290.15 + i,
                    "max": 300.15 + i,
                    "night": 288.15 + i,
                    "eve": 294.15 + i,
                    "morn": 291.15 + i,
                },
                "feels_like": {
                    "day": 296.15 + i,
                    "night": 288.15 + i,
                    "eve": 294.15 + i,
                    "morn": 291.15 + i,
                },
                "pressure": 1013 - i,
                "humidity": 55 + i * 5,
                "dew_point": 285.15 + i,
                "wind_speed": 3.5 + i,
                "wind_deg": 180 + i * 10,
                "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                "clouds": 20 + i * 10,
                "pop": 0.0 + i * 0.1,
                "uvi": 5.0,
            })
        
        response = client.post(
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
                    "daily": daily_data,
                },
            },
        )
        
        assert response.status_code == 200
        
        # Verify daily data in state
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        loc_key = list(state["locations"].keys())[0]
        loc_data = state["locations"][loc_key]
        
        assert loc_data["current_report"]["daily"] is not None
        assert len(loc_data["current_report"]["daily"]) == 3

    def test_update_with_alerts(self, client_with_engine):
        """Test updating weather with weather alerts."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        response = client.post(
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
                        "temp": 305.15,  # Hot!
                        "feels_like": 308.15,
                        "pressure": 1010,
                        "humidity": 70,
                        "dew_point": 295.15,
                        "uvi": 9.0,
                        "clouds": 5,
                        "visibility": 10000,
                        "wind_speed": 2.0,
                        "wind_deg": 180,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
                    },
                    "alerts": [
                        {
                            "sender_name": "NWS Philadelphia - Mount Holly",
                            "event": "Excessive Heat Warning",
                            "start": now,
                            "end": now + 86400,
                            "description": "Heat index values up to 115. This is a dangerous situation.",
                            "tags": ["Extreme temperature value"],
                        },
                        {
                            "sender_name": "NWS Philadelphia - Mount Holly",
                            "event": "Air Quality Alert",
                            "start": now,
                            "end": now + 43200,
                            "description": "Code Orange air quality expected.",
                            "tags": ["Air quality"],
                        },
                    ],
                },
            },
        )
        
        assert response.status_code == 200
        
        # Verify alerts in state
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        loc_key = list(state["locations"].keys())[0]
        loc_data = state["locations"][loc_key]
        
        assert loc_data["current_report"]["alerts"] is not None
        assert len(loc_data["current_report"]["alerts"]) == 2
        
        alert_events = [a["event"] for a in loc_data["current_report"]["alerts"]]
        assert "Excessive Heat Warning" in alert_events
        assert "Air Quality Alert" in alert_events

    def test_update_different_location_creates_separate_entry(self, client_with_engine):
        """Test that updates to different locations create separate entries."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        # Create base report structure
        def make_report(lat, lon, timezone):
            return {
                "lat": lat,
                "lon": lon,
                "timezone": timezone,
                "timezone_offset": -18000 if "New_York" in timezone else -28800,
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
            }
        
        # Add NYC weather
        response1 = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": make_report(40.7128, -74.0060, "America/New_York"),
            },
        )
        assert response1.status_code == 200
        
        # Add LA weather
        response2 = client.post(
            "/weather/update",
            json={
                "latitude": 34.0522,
                "longitude": -118.2437,
                "report": make_report(34.0522, -118.2437, "America/Los_Angeles"),
            },
        )
        assert response2.status_code == 200
        
        # Verify both locations exist
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        assert state["update_count"] == 2
        assert len(state["locations"]) == 2

    def test_update_validates_required_fields(self, client_with_engine):
        """Test that update validates required fields in report."""
        client, engine = client_with_engine
        
        # Missing latitude
        response = client.post(
            "/weather/update",
            json={
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                },
            },
        )
        assert response.status_code == 422
        
        # Missing longitude
        response = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                },
            },
        )
        assert response.status_code == 422
        
        # Missing report
        response = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )
        assert response.status_code == 422

    def test_update_validates_report_structure(self, client_with_engine):
        """Test that update validates report has required structure.
        
        Per WeatherReport model, report requires:
        - lat: float
        - lon: float
        - timezone: str
        - timezone_offset: int
        """
        client, engine = client_with_engine
        
        # Empty report
        response = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {},
            },
        )
        assert response.status_code == 422
        
        # Missing timezone
        response = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                },
            },
        )
        assert response.status_code == 422

    def test_state_reflects_latest_update(self, client_with_engine):
        """Test that state reflects the most recent update for a location."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        def make_report(temp):
            return {
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York",
                "timezone_offset": -18000,
                "current": {
                    "dt": now,
                    "sunrise": now - 3600,
                    "sunset": now + 36000,
                    "temp": temp,
                    "feels_like": temp,
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
            }
        
        # First update
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": make_report(290.15),  # Cold
            },
        )
        
        # Second update with different temperature
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": make_report(300.15),  # Warmer
            },
        )
        
        # State should reflect latest update
        state_response = client.get("/weather/state")
        state = state_response.json()
        
        loc_key = list(state["locations"].keys())[0]
        loc_data = state["locations"][loc_key]
        
        assert loc_data["current_report"]["current"]["temp"] == 300.15  # Latest value

    def test_update_increments_update_count(self, client_with_engine):
        """Test that each update increments the update_count."""
        client, engine = client_with_engine
        
        now = int(time.time())
        
        def make_report(lat, lon):
            return {
                "lat": lat,
                "lon": lon,
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
            }
        
        # Initial state
        state_response = client.get("/weather/state")
        assert state_response.json()["update_count"] == 0
        
        # First update
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": make_report(40.7128, -74.0060),
            },
        )
        state_response = client.get("/weather/state")
        assert state_response.json()["update_count"] == 1
        
        # Second update (same location)
        client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": make_report(40.7128, -74.0060),
            },
        )
        state_response = client.get("/weather/state")
        assert state_response.json()["update_count"] == 2
        
        # Third update (different location)
        client.post(
            "/weather/update",
            json={
                "latitude": 34.0522,
                "longitude": -118.2437,
                "report": make_report(34.0522, -118.2437),
            },
        )
        state_response = client.get("/weather/state")
        assert state_response.json()["update_count"] == 3
