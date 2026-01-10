# Backend

## Running the server

To run the server, execute the following command from the root of the project:

```bash
python -m uvicorn backend.main:app --reload
```

Or: 

```bash
uivcorn backend.main:app --reload 
```

## Testing Redis 

Run `redis-cli ZRANGE triage_queue 0 -1 WITHSCORES`
