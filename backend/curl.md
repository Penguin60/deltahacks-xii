# API Testing with curl

## POST /invoke - Process transcript through 3-agent pipeline

### Example 1: Armed Robbery
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "text": "There is an armed robbery happening at the convenience store on King Street. The suspect has a gun and is threatening the cashier. Please send help immediately!",
    "time": "2026-01-10T14:30:00",
    "location": "M5H 2N2, Toronto"
  }'
```

**Expected output structure:**
```json
{
  "result": {
    "id": "<ULID>",
    "incidentType": "Armed Robbery",
    "location": "M5H2N2",
    "date": "1/10/2026",
    "time": "14:30",
    "message": "There is an armed robbery happening...",
    "desc": "Armed robbery in progress at convenience store with armed suspect",
    "suggested_actions": "dispatch officer",
    "status": "in progress",
    "severity_level": "3"
  }
}
```

### Example 2: Fire Emergency
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My house is on fire! Flames coming from the kitchen. Address is 123 Main Street, apartment 4B. We need firefighters now!",
    "time": "2026-01-10T09:15:00",
    "location": "V6B 1A1, Vancouver"
  }'
```

**Expected:** `severity_level: "3"`, `suggested_actions: "dispatch firefighters"`

### Example 3: Public Nuisance
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "text": "There is a group of people making a lot of noise outside my apartment. Its 2 AM and they are being really loud with music.",
    "time": "2026-01-10T02:00:00",
    "location": "K1A 0B1, Ottawa"
  }'
```

**Expected:** `severity_level: "1"`, `suggested_actions: "console"` or `"dispatch officer"`

## GET /queue - View current triage queue
```bash
curl http://localhost:8000/queue
```

**Note:** The `/queue` endpoint currently returns from dummy-queue.json (not live Redis data)