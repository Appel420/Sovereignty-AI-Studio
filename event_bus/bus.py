async def _get_redis():
    """Return a redis.asyncio client, creating it on first call."""
    global _redis_client
    if _redis_client is None and _REDIS_URL:
        try:
            import redis.asyncio as aioredis
            _redis_client = await aioredis.from_url(_REDIS_URL)
            logger.info("Event bus connected to Redis at %s", _REDIS_URL)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            _redis_client = None
    return _redis_client