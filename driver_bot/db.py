from shared.database import execute, fetchrow


async def get_driver(user_id):
    return await fetchrow("SELECT * FROM drivers WHERE user_id=$1", user_id)


async def save_driver(user_id, username, phone, brand, model, color, plate):
    await execute("""
        INSERT INTO drivers (user_id, username, phone, brand, model, color, plate)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (user_id) DO UPDATE SET
        username=EXCLUDED.username,
        phone=EXCLUDED.phone,
        brand=EXCLUDED.brand,
        model=EXCLUDED.model,
        color=EXCLUDED.color,
        plate=EXCLUDED.plate
    """, user_id, username, phone, brand, model, color, plate)
