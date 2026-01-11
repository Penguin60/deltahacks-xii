# backend JSON specifications 


Data flow: Twilo API -> speech to text API -> transcript -> call_agent (agent1) -> assessment_agent (agent2) -> middleware function 
-> triage_agent (agent3) -> queue 

Agent 1: extracts caller's provided information into a summary JSON
Agent 2: adds suggested action and summarization 
Agent 3: threat ranking and reassessment 


## transcript JSON

```JSON
{
    "text": string;
    "time": "HH:MM"; // hours: minutes 
    "location": string; // may be nonsense, the call agent will extract from this and output JSON 
    "duration": "MM:SS" // minutes and seconds 
}
```

## call_agent JSON output 

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack" | "other";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "duration": "MM:SS";
    "mesage": string; // the original message from the transcript 
}
```

## The input to assessment_agent:

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack" | "other";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "duration": "MM:SS";
    "mesage": string; // the original message from the transcript 
    "desc": "None"; // an AI generated one line description. IMPORTANT: The Ai agent is instructed to output a JSON without this field, 
    // and this is added via code.
    "suggested_actions": "none"; // the AI agent is instructed to output a JSON without this field, and this is added via code.
    "status": "called"; // the possible options are "called", "in progress", or "completed", but at this state it must be "called", the AI agent is instructed to output a JSON without this field, and this is added via code.
    "severity_level": "none"; // the possible options are "1", "2", "3" or "none" but at this state it is "none" only.
}


Constraints: the above must follow the expected formats. call_agent JSON has the same fields as triage_agent but has limitations on what it can output.

## assessment_agent JSON output:

```JSON 
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack" | "other";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "duration": "MM:SS";
    "mesage": string; // the original message from the transcript 
    "desc": string; // the AI agent outputs a summary based on the message
    "suggested_actions": "console" | "ask for more details" | "dispatch officer" | "dispatch first-aiders" | "dispatch firefighters"; // the AI agent is instructed to output a JSON without this field, and this is added via code.
    "status": "called" ; // the possible options are "called", "in progress", or "completed", but at this state it must be "called", the AI agent is instructed to output a JSON without this field, and this is added via code.
    "severity_level": "none"; // the possible options are "1", "2", "3" or "none" but at this state it is "none" only.
}
```


## the input to triage_agent:

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack" | "other";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "duration": "MM:SS";
    "mesage": string; // the original message from the transcript 
    "desc": string; // the AI agent outputs a summary based on the message
    "suggested_actions": "console" | "ask for more details" | "dispatch officer" | "dispatch first-aiders" | "dispatch firefighters"; // the AI agent is instructed to output a JSON without this field, and this is added via code.
    "status": "called" ; // this value is changed to "in progress when the triage_agent outputs"
    "severity_level": "none"; // this value is changed when the triage_agent outputs
}
```

## triage_agent JSON output 

The triage agent's output is what the Redis sorted set stores.

```JSON
{
    "id": ULID; // unix timestamp generates a ULID
    "incidentType": "Public Nuisance" | "Break In" | "Armed Robbery" | "Car Theft" | "Theft" | "PickPocket" | "Fire" | "Mass Fire" | "Crowd Stampede" | "Terrorist Attack";
    "location": Canadian postal code as a string: Letter-Number-Letter-Number-Letter-Number as string; 
    "date": "month/day/year" as string;
    "time": "04:19" 24 hour time as string;
    "duration": "MM:SS";
    "mesage": string; // the original message from the transcript 
    "desc": string; // an AI generated one line description 
    "suggested_actions": "console" | "ask for more details" | "dispatch officer" | "dispatch first-aiders" | "dispatch firefighters";
    "status": "in progress"; // the other fields, such as "called" and "completed", must be hard coded to this value, because the call is pushed to the Redis queue afterwards. 
    "severity_level": "1" | "2" | "3"; // 1 is for nuisance, minor injuries and non threatening, 2 is for injuries inflicted and potentially life threatening, 3 is for life threatening, urgent and immediate action required. This is assessed and classified by the final agent (agent 3).
}
```

