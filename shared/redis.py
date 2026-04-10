import os
import redis.asyncio as redis

redis_client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
