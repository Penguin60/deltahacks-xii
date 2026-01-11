# API Testing with curl

## POST /invoke - Process transcript through 3-agent pipeline

### Example 1: Fire Emergency (with full data structure)
```bash
curl -X POST http://localhost:8000/invoke \\
  -H "Content-Type: application/json" \\
  -d '{
    "transcript": {
      "text": "My house is on fire! I need help immediately. The address is 123 Maple Street, apartment 4B.",
      "time": "2026-01-10T09:15:00Z",
      "location": "V6B1A1",
      "duration": "00:35"
    },
    "timestamped_transcript": {
      "transcript": [
        { "text": "My house is on fire!", "time": "00:02" },
        { "text": "I need help immediately.", "time": "00:05" },
        { "text": "The address is 123 Maple Street, apartment 4B.", "time": "00:10" }
      ]
    }
  }'
```

**Expected output structure:**
```json
{
  "result": {
    "id": "<ULID>",
    "incidentType": "Fire",
    "location": "V6B1A1",
    "date": "1/10/2026",
    "time": "09:15",
    "duration": "00:35",
    "message": "My house is on fire! I need help immediately. The address is 123 Maple Street, apartment 4B.",
    "desc": "House on fire, flames from kitchen. Firefighters needed.",
    "suggested_actions": "dispatch firefighters",
    "status": "in progress",
    "severity_level": "3"
  }
}
```

### Example 2: Armed Robbery
```bash
curl -X POST http://localhost:8000/invoke \\
  -H "Content-Type: application/json" \\
  -d '{
    "transcript": {
      "text": "There is an armed robbery happening at the convenience store on King Street. The suspect has a gun and is threatening the cashier. Please send help immediately!",
      "time": "2026-01-10T14:30:00Z",
      "location": "M5H2N2",
      "duration": "03:52"
    },
    "timestamped_transcript": {
      "transcript": [
        { "text": "There is an armed robbery happening", "time": "00:01" },
        { "text": "at the convenience store on King Street.", "time": "00:04" },
        { "text": "The suspect has a gun and is threatening the cashier.", "time": "00:08" },
        { "text": "Please send help immediately!", "time": "00:10" }
      ]
    }
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
    "duration": "03:52",
    "message": "There is an armed robbery happening...",
    "desc": "Armed robbery in progress at convenience store with armed suspect",
    "suggested_actions": "dispatch officer",
    "status": "in progress",
    "severity_level": "3"
  }
}
```

### Example 3: Public Nuisance
```bash
curl -X POST http://localhost:8000/invoke \\
  -H "Content-Type: application/json" \\
  -d '{
    "transcript": {
      "text": "There is a group of people making a lot of noise outside my apartment. Its 2 AM and they are being really loud with music.",
      "time": "2026-01-10T02:00:00Z",
      "location": "K1A0B1",
      "duration": "01:20"
    },
    "timestamped_transcript": {
      "transcript": [
        { "text": "There is a group of people making a lot of noise", "time": "00:01" },
        { "text": "outside my apartment. Its 2 AM and they are being really loud with music.", "time": "00:07" }
      ]
    }
  }'
```

**Expected output structure:**
```json
{
  "result": {
    "id": "<ULID>",
    "incidentType": "Public Nuisance",
    "location": "K1A0B1",
    "date": "1/10/2026",
    "time": "02:00",
    "duration": "01:20",
    "message": "There is a group of people making a lot of noise...",
    "desc": "Loud noise complaint from apartment building at 2 AM.",
    "suggested_actions": "console",
    "status": "in progress",
    "severity_level": "1"
  }
}


## GET /queue - View current triage queue
```bash
curl http://localhost:8000/queue
```

**Note:** The `/queue` endpoint currently returns from dummy-queue.json (not live Redis data)

## GET /agent/{ulid} - Retrieve a single incident from Pinecone
```bash
curl http://localhost:8000/agent/01H8XGJWBWBAQ4J1VDB1M9X519
```

**Note:** The ULID above matches the first record in `sample_incidents.json`.