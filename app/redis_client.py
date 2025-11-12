import redis
import json
import os
from typing import Any, Optional

# Redis connection - Railway uses REDIS_PUBLIC_URL
redis_url = os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
print(f"Using Redis URL: {redis_url[:50]}..." if redis_url else "No Redis URL found")
redis_client = redis.from_url(redis_url, decode_responses=True)

class RedisCache:
    @staticmethod
    def set(key: str, value: Any, expire: int = 3600):
        """Set value in Redis with expiration"""
        try:
            redis_client.setex(key, expire, json.dumps(value))
            return True
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    @staticmethod
    def delete(key: str):
        """Delete key from Redis"""
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    @staticmethod
    def exists(key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return redis_client.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False