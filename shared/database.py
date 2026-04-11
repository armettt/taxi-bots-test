import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "neondb")

pool: asyncpg.Pool | None = None


# ---------------- INIT DB ----------------
async def init_db():
    global pool

    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL)

        async with pool.acquire() as conn:
            await conn.execute(f"SET search_path TO {DB_SCHEMA}")


# ---------------- INTERNAL SAFETY ----------------
async def _get_pool():
    if pool is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return pool


# ---------------- QUERIES ----------------
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


# ---------------- CLOSE DB ----------------
async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
