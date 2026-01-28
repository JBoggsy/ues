# API Authentication

This guide covers authentication and authorization for the UES REST API.

## Overview

All UES API endpoints (except a few utility endpoints) require authentication via API key. The authentication system provides:

- **API Key Authentication**: All requests require a valid `X-API-Key` header
- **Fine-grained Permissions**: Each endpoint has a specific permission; keys can be granted any subset
- **Admin Key Generation**: An admin key with full access is generated at server startup
- **Key Management**: Create, list, and revoke API keys via `/keys` endpoints
- **Access Logging**: All API requests are logged for audit purposes

## Quick Start

### 1. Get the Admin Key

When you start the UES server, an admin API key is printed to the console:

```bash
$ uv run uvicorn ues.main:app --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
🔑 Admin API Key: ues_a1b2c3d4e5f6g7h8...
   Key ID: ues_12345678
```

**Save this key!** It won't be shown again. This admin key has full access (`*` permission) to all endpoints.

### 2. Use the Key in Requests

Include the API key in the `X-API-Key` header:

```bash
# Using curl
curl -H "X-API-Key: ues_a1b2c3d4e5f6g7h8..." http://localhost:8000/simulation/status

# Using httpie
http GET http://localhost:8000/simulation/status X-API-Key:ues_a1b2c3d4e5f6g7h8...
```

### 3. Use the Python Client

The Python client handles authentication automatically:

```python
from ues.client import UESClient

# Pass API key when creating the client
with UESClient(api_key="ues_a1b2c3d4e5f6g7h8...") as client:
    client.simulation.start()
    status = client.simulation.status()
    print(f"Simulation running: {status.is_running}")
```

For async usage:

```python
from ues.client import AsyncUESClient

async with AsyncUESClient(api_key="ues_a1b2c3d4e5f6g7h8...") as client:
    await client.simulation.start()
    status = await client.simulation.status()
```

---

## Authentication Details

### Request Header

All authenticated requests must include:

```
X-API-Key: <your-api-key>
```

### Error Responses

| Status Code | Meaning |
|-------------|---------|
| 401 Unauthorized | Missing or invalid API key |
| 403 Forbidden | Valid key but insufficient permissions |

**401 Response Example:**
```json
{
  "detail": "Invalid API key"
}
```

**403 Response Example:**
```json
{
  "detail": "Permission denied: requires 'simulation:start'"
}
```

### Unauthenticated Endpoints

The following endpoints do NOT require authentication:

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Root welcome message |
| `GET /health` | Health check (for load balancers) |
| `GET /docs` | Swagger UI documentation |
| `GET /redoc` | ReDoc documentation |
| `GET /openapi.json` | OpenAPI schema |

---

## Key Management

### Create a New Key

```bash
POST /keys
X-API-Key: <admin-key>
Content-Type: application/json

{
  "name": "my-agent-key",
  "permissions": ["email:*", "sms:*", "simulation:status"]
}
```

**Response:**
```json
{
  "key_id": "ues_87654321",
  "name": "my-agent-key",
  "secret": "ues_secret_abc123...",
  "permissions": ["email:*", "sms:*", "simulation:status"],
  "created_at": "2025-01-15T10:30:00Z"
}
```

> **Important**: The `secret` field is only returned once at creation time. Store it securely!

### List All Keys

```bash
GET /keys
X-API-Key: <admin-key>
```

**Response:**
```json
{
  "keys": [
    {
      "key_id": "ues_12345678",
      "name": "admin",
      "permissions": ["*"],
      "created_at": "2025-01-15T10:00:00Z"
    },
    {
      "key_id": "ues_87654321",
      "name": "my-agent-key",
      "permissions": ["email:*", "sms:*", "simulation:status"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Get Key Details

```bash
GET /keys/{key_id}
X-API-Key: <admin-key>
```

### Revoke a Key

```bash
DELETE /keys/{key_id}
X-API-Key: <admin-key>
```

---

## Permissions

### Permission Format

Permissions follow the pattern: `{resource}:{action}` or `{resource}:{sub-resource}:{action}`

Examples:
- `email:send` - Send emails
- `simulation:start` - Start the simulation
- `calendar:calendars:create` - Create calendars (sub-resource)

### Wildcard Permissions

| Pattern | Meaning |
|---------|---------|
| `*` | Full admin access (all permissions) |
| `email:*` | All email operations |
| `calendar:*` | All calendar operations (includes sub-resources) |
| `simulation:*` | All simulation control operations |

### Complete Permission List

#### Time Control (`/simulator/time`)
| Endpoint | Permission |
|----------|------------|
| `GET /simulator/time` | `time:read` |
| `POST /simulator/time/advance` | `time:advance` |
| `POST /simulator/time/set` | `time:set` |
| `POST /simulator/time/skip-to-next` | `time:skip` |
| `POST /simulator/time/set-scale` | `time:scale` |
| `POST /simulator/time/pause` | `time:pause` |
| `POST /simulator/time/resume` | `time:resume` |

#### Environment (`/environment`)
| Endpoint | Permission |
|----------|------------|
| `GET /environment/state` | `environment:read` |
| `GET /environment/modalities` | `environment:list` |
| `POST /environment/validate` | `environment:validate` |

#### Events (`/events`)
| Endpoint | Permission |
|----------|------------|
| `GET /events` | `events:list` |
| `POST /events` | `events:create` |
| `POST /events/immediate` | `events:execute` |
| `POST /events/batch` | `events:batch` |
| `GET /events/next` | `events:read` |
| `GET /events/summary` | `events:summary` |
| `GET /events/{event_id}` | `events:read` |
| `DELETE /events/{event_id}` | `events:delete` |

#### Simulation (`/simulation`)
| Endpoint | Permission |
|----------|------------|
| `POST /simulation/start` | `simulation:start` |
| `POST /simulation/stop` | `simulation:stop` |
| `GET /simulation/status` | `simulation:status` |
| `POST /simulation/reset` | `simulation:reset` |
| `POST /simulation/clear` | `simulation:clear` |
| `POST /simulation/undo` | `simulation:undo` |
| `POST /simulation/redo` | `simulation:redo` |
| `POST /simulation/hold` | `simulation:hold` |
| `POST /simulation/release/{hold_id}` | `simulation:release` |
| `GET /simulation/holds` | `simulation:holds` |

#### Scenario (`/scenario`)
| Endpoint | Permission |
|----------|------------|
| `GET /scenario/export/environment` | `scenario:export` |
| `GET /scenario/export/events` | `scenario:export` |
| `GET /scenario/export/full` | `scenario:export` |
| `POST /scenario/import/environment` | `scenario:import` |
| `POST /scenario/import/events` | `scenario:import` |
| `POST /scenario/import/full` | `scenario:import` |

#### Webhooks (`/webhooks`)
| Endpoint | Permission |
|----------|------------|
| `POST /webhooks` | `webhooks:create` |
| `GET /webhooks` | `webhooks:list` |
| `GET /webhooks/{id}` | `webhooks:read` |
| `PATCH /webhooks/{id}` | `webhooks:update` |
| `DELETE /webhooks/{id}` | `webhooks:delete` |
| `POST /webhooks/{id}/test` | `webhooks:test` |
| `GET /webhooks/{id}/deliveries` | `webhooks:deliveries` |
| `POST /webhooks/{id}/pause` | `webhooks:pause` |
| `POST /webhooks/{id}/resume` | `webhooks:resume` |

#### Email (`/email`)
| Endpoint | Permission |
|----------|------------|
| `GET /email/state` | `email:state` |
| `POST /email/query` | `email:query` |
| `POST /email/send` | `email:send` |
| `POST /email/receive` | `email:receive` |
| `POST /email/read` | `email:read` |
| `POST /email/unread` | `email:unread` |
| `POST /email/star` | `email:star` |
| `POST /email/unstar` | `email:unstar` |
| `POST /email/archive` | `email:archive` |
| `POST /email/delete` | `email:delete` |
| `POST /email/label` | `email:label` |
| `POST /email/unlabel` | `email:unlabel` |
| `POST /email/move` | `email:move` |

#### SMS (`/sms`)
| Endpoint | Permission |
|----------|------------|
| `GET /sms/state` | `sms:state` |
| `POST /sms/query` | `sms:query` |
| `POST /sms/send` | `sms:send` |
| `POST /sms/receive` | `sms:receive` |
| `POST /sms/read` | `sms:read` |
| `POST /sms/unread` | `sms:unread` |
| `POST /sms/delete` | `sms:delete` |
| `POST /sms/react` | `sms:react` |
| `POST /sms/conversation` | `sms:conversation` |

#### Chat (`/chat`)
| Endpoint | Permission |
|----------|------------|
| `GET /chat/state` | `chat:state` |
| `POST /chat/query` | `chat:query` |
| `POST /chat/send` | `chat:send` |
| `POST /chat/delete` | `chat:delete` |
| `POST /chat/clear` | `chat:clear` |

#### Calendar (`/calendar`)
| Endpoint | Permission |
|----------|------------|
| `GET /calendar/state` | `calendar:state` |
| `POST /calendar/query` | `calendar:query` |
| `POST /calendar/create` | `calendar:create` |
| `POST /calendar/update` | `calendar:update` |
| `POST /calendar/delete` | `calendar:delete` |
| `GET /calendar/calendars` | `calendar:calendars:list` |
| `POST /calendar/calendars/create` | `calendar:calendars:create` |
| `POST /calendar/calendars/update` | `calendar:calendars:update` |
| `POST /calendar/calendars/delete` | `calendar:calendars:delete` |
| `POST /calendar/calendars/set-default` | `calendar:calendars:default` |

#### Location (`/location`)
| Endpoint | Permission |
|----------|------------|
| `GET /location/state` | `location:state` |
| `POST /location/query` | `location:query` |
| `POST /location/update` | `location:update` |

#### Weather (`/weather`)
| Endpoint | Permission |
|----------|------------|
| `GET /weather/state` | `weather:state` |
| `POST /weather/query` | `weather:query` |
| `POST /weather/update` | `weather:update` |

#### Key Management (`/keys`)
| Endpoint | Permission |
|----------|------------|
| `POST /keys` | `keys:create` |
| `GET /keys` | `keys:list` |
| `GET /keys/{key_id}` | `keys:read` |
| `DELETE /keys/{key_id}` | `keys:revoke` |

#### Access Logs (`/access-logs`)
| Endpoint | Permission |
|----------|------------|
| `GET /access-logs` | `logs:read` |
| `GET /access-logs/stats` | `logs:read` |
| `POST /access-logs/clear` | `logs:clear` |

---

## Common Permission Sets

Here are some common permission combinations for different use cases:

### Read-Only Agent

For an agent that only needs to observe the environment:

```json
{
  "name": "observer-agent",
  "permissions": [
    "time:read",
    "environment:read",
    "environment:list",
    "events:list",
    "events:read",
    "events:summary",
    "simulation:status",
    "email:state",
    "email:query",
    "sms:state",
    "sms:query",
    "chat:state",
    "chat:query",
    "calendar:state",
    "calendar:query",
    "calendar:calendars:list",
    "location:state",
    "location:query",
    "weather:state",
    "weather:query"
  ]
}
```

### Email-Only Agent

For an agent that only interacts with email:

```json
{
  "name": "email-agent",
  "permissions": [
    "simulation:status",
    "email:*"
  ]
}
```

### Full Modality Access

For an agent that needs to interact with all modalities but not control simulation:

```json
{
  "name": "assistant-agent",
  "permissions": [
    "simulation:status",
    "simulation:hold",
    "simulation:release",
    "time:read",
    "email:*",
    "sms:*",
    "chat:*",
    "calendar:*",
    "location:*",
    "weather:*"
  ]
}
```

### Scenario Manager

For a tool that manages scenario save/load:

```json
{
  "name": "scenario-manager",
  "permissions": [
    "scenario:export",
    "scenario:import",
    "simulation:status",
    "simulation:reset",
    "simulation:clear"
  ]
}
```

---

## Access Logging

All authenticated API requests are logged automatically. You can query the access logs to audit API usage.

### Query Access Logs

```bash
GET /access-logs?limit=100&key_name=my-agent
X-API-Key: <admin-key>
```

**Query Parameters:**
| Parameter | Description |
|-----------|-------------|
| `limit` | Max entries to return (default: 100) |
| `offset` | Pagination offset |
| `key_id` | Filter by key ID |
| `key_name` | Filter by key name |
| `path_prefix` | Filter by path prefix (e.g., `/email`) |
| `method` | Filter by HTTP method |
| `status_code_min` | Minimum status code |
| `status_code_max` | Maximum status code |
| `errors_only` | Only show failed requests |
| `since` | Only entries after this timestamp |
| `until` | Only entries before this timestamp |

### Get Access Statistics

```bash
GET /access-logs/stats
X-API-Key: <admin-key>
```

**Response:**
```json
{
  "total_requests": 1523,
  "successful_requests": 1498,
  "failed_requests": 25,
  "unique_keys": 3,
  "first_request": "2025-01-15T10:00:00Z",
  "last_request": "2025-01-15T14:30:00Z"
}
```

### Clear Access Logs

```bash
POST /access-logs/clear
X-API-Key: <admin-key>
```

---

## Event Attribution

When creating events via the API, the creating API key is automatically recorded:

- `agent_id` field defaults to the API key's `key_id` if not explicitly provided
- `metadata.created_by_key` is always set to the API key's `key_id`

This enables tracking which agent/key created each event for debugging and audit purposes.

**Example:**

```bash
POST /events
X-API-Key: ues_87654321...  # key_id: ues_87654321

{
  "scheduled_time": "2025-01-15T12:00:00Z",
  "modality": "email",
  "input": { ... }
}
```

The created event will have:
```json
{
  "event_id": "evt_...",
  "agent_id": "ues_87654321",
  "metadata": {
    "created_by_key": "ues_87654321"
  },
  ...
}
```

---

## Security Best Practices

1. **Secure the Admin Key**: The admin key is printed to console at startup. Ensure console output is protected in production.

2. **Use Least Privilege**: Create keys with only the permissions needed for each use case.

3. **Use HTTPS in Production**: API keys are transmitted in headers. Always use HTTPS to protect them in transit.

4. **Rotate Keys Periodically**: Revoke and recreate keys periodically, especially for production systems.

5. **Monitor Access Logs**: Regularly review access logs for suspicious activity.

6. **Don't Commit Keys**: Never commit API keys to version control. Use environment variables instead.

---

## Troubleshooting

### "Invalid API key" (401)

- Verify the key is correct (no extra whitespace)
- Ensure the key hasn't been revoked
- Check that the server was restarted (keys are in-memory only)

### "Permission denied" (403)

- List your key's permissions: `GET /keys/{key_id}`
- Compare against the required permission for the endpoint
- Create a new key with the needed permission or use the admin key

### Lost Admin Key

If you lose the admin key, restart the server. A new admin key will be generated and printed to the console.

> **Note**: Keys are stored in-memory only and do not persist across server restarts. This is by design for the development/testing focus of UES.
