# backend JSON specifications 

Data flow: Twilo API -> speech to text API -> transcript -> call_agent (agent1) -> triage_agent (agent2) -> queue 


## transcript JSON

```JSON
{
    "message": string 
}
```
constraints: None.


## call_agent JSON output 

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "mesage": string; // the original message from the transcript 
    "desc": string; // an AI generated one line description 
    "suggested_actions": "console" | "ask for more details" | "dispatch officer" | "dispatch first-aiders" | "dispatch firefighters";
}
```

Constraints: the above must follow the expected formats.


## triage_agent JSON output 

The triage agent's output is what the Redis sorted set stores.

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "mesage": string; // the original message from the transcript 
    "desc": string; // an AI generated one line description 
    "suggested_actions": "console" | "ask for more details" | "dispatch officer" | "dispatch first-aiders" | "dispatch firefighters";
    "severity_level": "1" | "2" | "3"; // 1 is for nuisance, minor injuries and non threatening, 2 is for injuries inflicted and potentially life threatening, 3 is for life threatening, urgent and immediate action required.
}
```

