"""
Demo PR: Add Redis caching to /users endpoint.

Triggers PRGenie to flag missing TTL + missing tests + sensitive
requirements.txt change.
"""
import json
import redis

r = redis.Redis(host="localhost", port=6379, db=0)


def get_user(user_id: int) -> dict | None:
    cached = r.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    user = db_fetch_user(user_id)
    r.set(f"user:{user_id}", json.dumps(user))
    return user


def db_fetch_user(user_id: int) -> dict:
    raise NotImplementedError
