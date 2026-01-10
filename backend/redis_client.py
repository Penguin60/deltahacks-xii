# backend/redis_client.py
import redis.asyncio as redis
import os

# Load connection details from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Create a reusable async Redis client instance.
# The client will manage connections from a connection pool automatically.
# `decode_responses=True` ensures that data is returned as strings.
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
