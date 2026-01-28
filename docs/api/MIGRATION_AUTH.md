# Migration Guide: API Authentication

This guide helps you migrate existing code to work with the new API authentication system introduced in UES.

## Breaking Changes Summary

The API authentication update introduces the following breaking changes:

1. **All API endpoints now require authentication** (except utility endpoints)
2. **Requests without a valid API key receive 401 Unauthorized**
3. **Events now include attribution metadata**

---

## Migration Steps

### Step 1: Obtain an API Key

When you start the UES server, an admin API key is automatically generated and printed to the console:

```bash
$ uv run uvicorn ues.main:app --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
🔑 Admin API Key: ues_a1b2c3d4e5f6g7h8...
   Key ID: ues_12345678
```

**Save this key immediately!** It's only shown once at startup.

### Step 2: Update Your Code

#### Python Client (Recommended)

**Before:**
```python
from ues.client import UESClient

with UESClient() as client:
    client.simulation.start()
```

**After:**
```python
from ues.client import UESClient

# Pass the API key when creating the client
with UESClient(api_key="ues_a1b2c3d4e5f6g7h8...") as client:
    client.simulation.start()
```

For async clients:

```python
from ues.client import AsyncUESClient

async with AsyncUESClient(api_key="ues_a1b2c3d4e5f6g7h8...") as client:
    await client.simulation.start()
```

#### Direct HTTP Requests (curl, httpie, requests)

**Before:**
```bash
curl http://localhost:8000/simulation/status
```

**After:**
```bash
curl -H "X-API-Key: ues_a1b2c3d4e5f6g7h8..." http://localhost:8000/simulation/status
```

**With Python `requests`:**

```python
import requests

# Before
response = requests.get("http://localhost:8000/simulation/status")

# After
headers = {"X-API-Key": "ues_a1b2c3d4e5f6g7h8..."}
response = requests.get("http://localhost:8000/simulation/status", headers=headers)
```

#### Using Environment Variables (Recommended for Production)

Store your API key in an environment variable:

```bash
export UES_API_KEY="ues_a1b2c3d4e5f6g7h8..."
```

Then in your code:

```python
import os
from ues.client import UESClient

api_key = os.environ["UES_API_KEY"]
with UESClient(api_key=api_key) as client:
    client.simulation.start()
```

### Step 3: Update Test Code

If you have tests that call the UES API, you'll need to include authentication.

**For pytest with the UES test fixtures:**

The `client_with_engine` fixture in `tests/api/conftest.py` automatically handles authentication. If you're using this fixture, no changes are needed.

**For custom test setups:**

```python
import pytest
from fastapi.testclient import TestClient
from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.main import app

@pytest.fixture
def authenticated_client():
    # Initialize API key registry and get admin key
    admin_secret, _admin_key = initialize_api_key_registry()
    
    # Create test client with auth header
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client
    
    shutdown_api_key_registry()
```

---

## Endpoints That Don't Require Authentication

The following endpoints remain accessible without authentication:

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Root welcome message |
| `GET /health` | Health check for load balancers |
| `GET /docs` | Swagger UI documentation |
| `GET /redoc` | ReDoc documentation |
| `GET /openapi.json` | OpenAPI schema |

---

## New Features Available After Migration

### Key Management

Create limited-permission keys for different use cases:

```python
# Using the admin key, create a limited key
response = requests.post(
    "http://localhost:8000/keys",
    headers={"X-API-Key": admin_key},
    json={
        "name": "email-only-agent",
        "permissions": ["email:*", "simulation:status"]
    }
)
new_key = response.json()["secret"]
```

### Access Logging

Monitor API usage:

```python
# Query access logs
response = requests.get(
    "http://localhost:8000/access-logs",
    headers={"X-API-Key": admin_key},
    params={"limit": 50, "errors_only": True}
)
```

### Event Attribution

Events now track which API key created them:

```python
# Create an event
client.events.create(
    scheduled_time=...,
    modality="email",
    input={...}
)
# The event will have:
# - agent_id: automatically set to your key_id
# - metadata.created_by_key: your key_id
```

---

## Common Migration Issues

### Issue: "Invalid API key" (401)

**Cause:** Missing or incorrect API key

**Solution:**
1. Verify you're including the `X-API-Key` header
2. Check for extra whitespace in the key
3. Ensure you're using the full key (starts with `ues_`)

### Issue: "Permission denied" (403)

**Cause:** Using a key without required permission

**Solution:**
1. Use the admin key (`*` permission), or
2. Create a new key with the needed permissions

### Issue: Tests Failing After Update

**Cause:** Tests not including API key

**Solution:** Update test fixtures to include authentication (see Step 3 above)

### Issue: Lost Admin Key

**Cause:** Didn't save the key at startup

**Solution:** Restart the server - a new admin key will be generated

---

## FAQ

### Q: Are API keys persisted across restarts?

No. Keys are stored in memory only. When you restart the server, all keys are lost and a new admin key is generated. This is intentional for UES's development/testing focus.

### Q: Can I disable authentication?

No. Authentication is always required. This ensures consistent security behavior.

### Q: What permissions does the admin key have?

The admin key has `*` permission, which grants access to all endpoints.

### Q: How do I create a key with limited permissions?

Use the `POST /keys` endpoint with your admin key:

```bash
curl -X POST http://localhost:8000/keys \
  -H "X-API-Key: <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "limited-key", "permissions": ["email:*"]}'
```

---

## Additional Resources

- **[AUTHENTICATION.md](AUTHENTICATION.md)** - Complete authentication documentation
- **[API_ACCESS_CONTROL.md](API_ACCESS_CONTROL.md)** - Implementation design details
- **[REST_API.md](REST_API.md)** - Full API reference
