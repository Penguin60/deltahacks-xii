```bash
curl -X POST http://localhost:8000/invoke -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "This is a test of the new langgraph endpoint."}]}'
```

```bash
curl http://localhost:8000/queue
```