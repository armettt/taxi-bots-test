from shared.database import execute, fetchrow

async def get_user(user_id: int):
    return await fetchrow("SELECT phone FROM users WHERE user_id=$1", user_id)

async def save_user(user_id: int, phone: str):
    await execute("""
    INSERT INTO users(user_id, phone)
    VALUES($1, $2)
    ON CONFLICT(user_id) DO UPDATE SET phone=EXCLUDED.phone
    """, user_id, phone)

async def create_order(data: dict):
    row = await fetchrow("""
    INSERT INTO orders(client_id, phone, username, from_loc, to_loc, comment)
    VALUES($1, $2, $3, $4, $5, $6)
    RETURNING id
    """, data["client_id"], data["phone"], data["username"],
        data["from_loc"], data["to_loc"], data["comment"])
    return row["id"]

async def get_order(order_id: int):
    return await fetchrow("SELECT * FROM orders WHERE id=$1", order_id)

async def update_order_status(order_id: int, status: str, driver_id: int | None = None, message_id: int | None = None):
    await execute("""
    UPDATE orders SET status=$1, driver_id=COALESCE($2, driver_id), message_id=COALESCE($3, message_id)
    WHERE id=$4
    """, status, driver_id, message_id, order_id)

async def delete_order(order_id: int):
    await execute("DELETE FROM orders WHERE id=$1", order_id)
