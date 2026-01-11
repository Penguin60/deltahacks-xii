# Backend

## Running the server

To run the server

1.execute the following command from the root of the project:
2. run the redis server on your machine


Step 1:
```bash
python -m uvicorn backend.main:app --reload
```

Or: 

```bash
uivcorn backend.main:app --reload 
```

Step 2:
Homebrew
```bash
brew services start redis 
```

redis-server
```bash

redis-server
```

## Testing Redis 

Run `redis-cli ZRANGE triage_queue 0 -1 WITHSCORES` in the terminal after querying to check the dump


## Adding sample data 

``