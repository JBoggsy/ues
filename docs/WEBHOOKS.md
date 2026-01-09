# Webhook API Documentation

This document describes the Webhook API for receiving event notifications via HTTP callbacks in UES.

## Overview

Webhooks provide HTTP callback notifications for external services to receive simulation events. Unlike WebSockets (which require persistent connections), webhooks push event data to registered HTTP endpoints that your service exposes.

**Use webhooks when:**
- Your AI agent runs as a separate HTTP service
- Using serverless functions (AWS Lambda, Cloud Functions)
- Integrating with external systems that can't maintain WebSocket connections
- Need guaranteed delivery with retry logic
- Building audit/logging services

**Use WebSockets when:**
- Building real-time UIs or dashboards
- Need bi-directional communication
- Can maintain persistent connections
- Want lowest possible latency

### Comparison with WebSocket API

| Aspect | WebSocket | Webhook |
|--------|-----------|---------|
| **Connection Model** | Client connects to server | Server POSTs to client URL |
| **Client Requirement** | Maintain open connection | Expose HTTP endpoint |
| **Registration** | Connect to `/ws` | POST to `/webhooks` |
| **Delivery Guarantee** | None (missed if disconnected) | Retries, delivery tracking |
| **Use Case** | Real-time UIs | External agents, serverless |
| **Event Filtering** | Send subscribe message | Specify `events` at registration |

## Quick Start

### 1. Register a Webhook

```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://my-agent.example.com/callback",
    "events": ["email.", "sms.received"],
    "secret": "my-secret-key"
  }'
```

Response:
```json
{
  "id": "wh_abc123def456",
  "url": "https://my-agent.example.com/callback",
  "events": ["email.", "sms.received"],
  "status": "active",
  "created_at": "2025-01-01T10:00:00Z",
  "has_secret": true
}
```

### 2. Receive Events

Your endpoint will receive POST requests with event payloads:

```json
{
  "id": "del_xyz789",
  "webhook_id": "wh_abc123def456",
  "event_type": "email.received",
  "timestamp": "2025-01-01T10:05:00Z",
  "data": {
    "email_id": "msg_123",
    "from": "sender@example.com",
    "subject": "Hello World"
  }
}
```

### 3. Test Your Webhook

```bash
curl -X POST http://localhost:8000/webhooks/wh_abc123def456/test
```

---

## API Reference

### Register Webhook

**POST** `/webhooks`

Create a new webhook registration.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Callback URL to POST events to |
| `events` | string[] | No | Event type patterns (null = all events) |
| `secret` | string | No | HMAC secret for signature verification |
| `metadata` | object | No | Custom metadata (e.g., agent name) |

**Event Patterns:**
- Exact match: `"email.received"` - only that event type
- Prefix match: `"email."` - all email events
- All events: `null` or omit the field

**Response:** `201 Created`

```json
{
  "id": "wh_abc123def456",
  "url": "https://example.com/callback",
  "events": ["email."],
  "status": "active",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:00:00Z",
  "metadata": {},
  "failure_count": 0,
  "last_delivery_at": null,
  "last_failure_at": null,
  "has_secret": true
}
```

---

### List Webhooks

**GET** `/webhooks`

List all registered webhooks with optional filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status: `active`, `paused`, `disabled` |
| `limit` | int | 50 | Maximum results (max 200) |
| `offset` | int | 0 | Pagination offset |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "wh_abc123",
      "url": "https://example.com/callback",
      "events": ["email."],
      "status": "active",
      ...
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### Get Webhook

**GET** `/webhooks/{webhook_id}`

Get details of a specific webhook.

**Response:** `200 OK`

Returns the webhook registration object.

**Errors:**
- `404 Not Found` - Webhook doesn't exist

---

### Update Webhook

**PATCH** `/webhooks/{webhook_id}`

Update webhook configuration. Only provided fields are updated.

**Request Body:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | New callback URL |
| `events` | string[] | New event patterns |
| `secret` | string | New HMAC secret |
| `metadata` | object | New metadata |
| `status` | string | New status (`active`, `paused`) |

**Response:** `200 OK`

Returns the updated webhook registration.

---

### Delete Webhook

**DELETE** `/webhooks/{webhook_id}`

Permanently delete a webhook registration.

**Response:** `204 No Content`

---

### Test Webhook

**POST** `/webhooks/{webhook_id}/test`

Send a test event to verify connectivity.

**Response:** `200 OK`

```json
{
  "webhook_id": "wh_abc123",
  "success": true,
  "response_status": 200,
  "response_time_ms": 45.2,
  "response_body": "OK",
  "error_message": null
}
```

---

### Pause Webhook

**POST** `/webhooks/{webhook_id}/pause`

Temporarily pause a webhook. Events will not be delivered while paused.

**Response:** `200 OK`

Returns the webhook with `status: "paused"`.

---

### Resume Webhook

**POST** `/webhooks/{webhook_id}/resume`

Resume a paused webhook. Also resets failure count and can re-enable disabled webhooks.

**Response:** `200 OK`

Returns the webhook with `status: "active"`.

---

### Get Delivery History

**GET** `/webhooks/{webhook_id}/deliveries`

Get recent delivery attempts for debugging.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum results (max 200) |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "del_xyz789",
      "webhook_id": "wh_abc123",
      "event_type": "email.received",
      "status": "delivered",
      "attempt_count": 1,
      "created_at": "2025-01-01T10:05:00Z",
      "delivered_at": "2025-01-01T10:05:00.150Z",
      "response_status": 200,
      "response_time_ms": 150.5,
      "error_message": null
    }
  ],
  "total": 1
}
```

---

## Event Payload Format

All webhook deliveries use this consistent format:

```json
{
  "id": "del_xyz789",
  "webhook_id": "wh_abc123def456",
  "event_type": "email.received",
  "timestamp": "2025-01-01T10:05:00Z",
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique delivery ID (for deduplication) |
| `webhook_id` | string | Your webhook registration ID |
| `event_type` | string | Event type (e.g., `email.received`) |
| `timestamp` | string | ISO 8601 timestamp of the event |
| `data` | object | Event-specific payload |

### Event Types

UES broadcasts events for all modality state changes. Common event types include:

| Event Type | Description |
|------------|-------------|
| `email.received` | New email received |
| `email.sent` | Email sent |
| `email.read` | Email marked as read |
| `email.deleted` | Email deleted |
| `sms.received` | SMS message received |
| `sms.sent` | SMS message sent |
| `calendar.created` | Calendar event created |
| `calendar.updated` | Calendar event updated |
| `calendar.deleted` | Calendar event deleted |
| `chat.message` | Chat message sent |
| `location.updated` | Location changed |
| `weather.updated` | Weather data updated |
| `time.advanced` | Simulator time advanced |
| `time.paused` | Simulation paused |
| `time.resumed` | Simulation resumed |
| `simulation.started` | Simulation started |
| `simulation.stopped` | Simulation stopped |
| `simulation.reset` | Simulation reset |

For complete event type reference, see [WebSocket Documentation](WEBSOCKET.md).

---

## Security

### HMAC Signature Verification

When you provide a `secret` during registration, UES includes an `X-UES-Signature` header with each delivery. This header contains an HMAC-SHA256 signature of the request body.

**Signature Format:** `sha256=<hex_digest>`

### Python Verification Example

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not signature.startswith("sha256="):
        return False
    
    received = signature[7:]  # Remove "sha256=" prefix
    return hmac.compare_digest(expected, received)

# In your Flask/FastAPI handler:
@app.post("/webhook")
async def webhook_handler(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-UES-Signature", "")
    
    if not verify_signature(payload, signature, "my-secret"):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = json.loads(payload)
    # Process event...
```

### Node.js Verification Example

```javascript
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
    const expected = 'sha256=' + crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    
    return crypto.timingSafeEqual(
        Buffer.from(expected),
        Buffer.from(signature)
    );
}

// In your Express handler:
app.post('/webhook', (req, res) => {
    const signature = req.headers['x-ues-signature'] || '';
    const payload = JSON.stringify(req.body);
    
    if (!verifySignature(payload, signature, 'my-secret')) {
        return res.status(401).send('Invalid signature');
    }
    
    // Process event...
    res.status(200).send('OK');
});
```

---

## Python Client Library

The UES client library provides convenient methods for webhook management.

### Synchronous Usage

```python
from client import UESClient

with UESClient() as client:
    # Register a webhook
    webhook = client.webhooks.register(
        url="https://my-agent.example.com/callback",
        events=["email.", "sms.received"],
        secret="my-secret-key",
        metadata={"agent": "EmailBot"}
    )
    print(f"Registered: {webhook['id']}")
    
    # Test the webhook
    result = client.webhooks.test(webhook['id'])
    if result['success']:
        print(f"Test successful! Response time: {result['response_time_ms']}ms")
    else:
        print(f"Test failed: {result['error_message']}")
    
    # List all webhooks
    webhooks = client.webhooks.list()
    for wh in webhooks['items']:
        print(f"- {wh['id']}: {wh['url']} ({wh['status']})")
    
    # Pause a webhook
    client.webhooks.pause(webhook['id'])
    
    # Resume a webhook
    client.webhooks.resume(webhook['id'])
    
    # Get delivery history
    deliveries = client.webhooks.get_deliveries(webhook['id'])
    for d in deliveries['items']:
        print(f"  {d['event_type']}: {d['status']}")
    
    # Delete when done
    client.webhooks.delete(webhook['id'])
```

### Asynchronous Usage

```python
import asyncio
from client import AsyncUESClient

async def main():
    async with AsyncUESClient() as client:
        # Register a webhook
        webhook = await client.webhooks.register(
            url="https://my-agent.example.com/callback",
            events=["email."]
        )
        
        # Test connectivity
        result = await client.webhooks.test(webhook['id'])
        print(f"Test result: {result['success']}")
        
        # Update webhook
        updated = await client.webhooks.update(
            webhook['id'],
            events=["email.", "sms."]
        )
        
        # Clean up
        await client.webhooks.delete(webhook['id'])

asyncio.run(main())
```

---

## Building a Webhook Receiver

### Flask Example

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)
WEBHOOK_SECRET = "my-secret-key"

def verify_signature(payload, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return signature == f"sha256={expected}"

@app.route("/webhook", methods=["POST"])
def webhook():
    # Verify signature if secret was configured
    signature = request.headers.get("X-UES-Signature", "")
    if WEBHOOK_SECRET and signature:
        if not verify_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401
    
    event = request.json
    
    # Process the event
    print(f"Received: {event['event_type']}")
    print(f"Data: {event['data']}")
    
    # Always respond quickly (process async if needed)
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(port=8080)
```

### FastAPI Example

```python
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib

app = FastAPI()
WEBHOOK_SECRET = "my-secret-key"

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected}")

def process_event(event: dict):
    """Process the event asynchronously."""
    event_type = event["event_type"]
    data = event["data"]
    
    if event_type.startswith("email."):
        print(f"Email event: {event_type}")
        # Handle email events...
    elif event_type.startswith("sms."):
        print(f"SMS event: {event_type}")
        # Handle SMS events...

@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    payload = await request.body()
    signature = request.headers.get("X-UES-Signature", "")
    
    # Verify signature
    if WEBHOOK_SECRET and signature:
        if not verify_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    event = await request.json()
    
    # Process asynchronously to respond quickly
    background_tasks.add_task(process_event, event)
    
    return {"status": "received"}
```

---

## Best Practices

### 1. Respond Quickly

Always return a 2xx response immediately. Process events asynchronously if needed:

```python
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    event = await request.json()
    background_tasks.add_task(process_event, event)
    return {"status": "received"}  # Return immediately
```

### 2. Handle Retries Idempotently

UES retries failed deliveries. Use the `id` field to detect and handle duplicates:

```python
processed_ids = set()

def process_event(event):
    if event["id"] in processed_ids:
        return  # Already processed
    
    processed_ids.add(event["id"])
    # Process the event...
```

### 3. Use Event Patterns Wisely

Instead of subscribing to all events, use patterns to filter:

```python
# Good - specific patterns
webhook = client.webhooks.register(
    url="https://example.com/callback",
    events=["email.received", "sms.received"]  # Only new messages
)

# Less efficient - receives all events
webhook = client.webhooks.register(
    url="https://example.com/callback",
    events=None  # Gets everything
)
```

### 4. Monitor Webhook Health

Check delivery history to identify issues:

```python
deliveries = client.webhooks.get_deliveries(webhook_id)
failed = [d for d in deliveries["items"] if d["status"] == "failed"]
if failed:
    print(f"Warning: {len(failed)} failed deliveries")
```

### 5. Handle Auto-Disable

Webhooks are automatically disabled after 10 consecutive failures. Use `resume()` to re-enable and reset the counter:

```python
webhooks = client.webhooks.list(status="disabled")
for wh in webhooks["items"]:
    print(f"Re-enabling {wh['id']} (was disabled)")
    client.webhooks.resume(wh["id"])
```

---

## Troubleshooting

### Webhook Not Receiving Events

1. **Check webhook status**: Ensure it's `active`, not `paused` or `disabled`
2. **Verify URL accessibility**: UES must be able to reach your endpoint
3. **Check event patterns**: Your patterns must match the event types being broadcast
4. **Test the webhook**: Use `POST /webhooks/{id}/test` to verify connectivity

### Signature Verification Failing

1. **Check secret match**: Ensure the secret used for verification matches registration
2. **Use raw payload**: Verify against the raw request body, not parsed JSON
3. **Check encoding**: Both secret and payload should be UTF-8 encoded

### Webhook Auto-Disabled

Webhooks are disabled after 10 consecutive failures. To fix:

1. Check and fix the underlying issue (endpoint down, timeout, etc.)
2. Resume the webhook: `POST /webhooks/{id}/resume`
3. The failure counter resets to 0

### High Response Times

UES times out after 10 seconds. Optimize your handler:

1. Return 200 immediately
2. Process events asynchronously
3. Avoid blocking operations in the request handler
