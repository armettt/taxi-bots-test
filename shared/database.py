async def _get_pool():
    if pool is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return pool


async def fetch(query, *args):
    p = await _get_pool()
    async with p.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query, *args):
    p = await _get_pool()
    async with p.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query, *args):
    p = await _get_pool()
    async with p.acquire() as conn:
        return await conn.execute(query, *args)
