from shared.database import fetchrow, execute

# ---------------- USERS ----------------
async def get_user(user_id):
    return await fetchrow(
        "SELECT phone FROM users WHERE user_id=$1",
        user_id
    )


async def save_user(user_id, phone):
    await execute("""
        INSERT INTO users (user_id, phone)
        VALUES ($1, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET phone = EXCLUDED.phone
    """, user_id, phone)


# ---------------- ORDERS ----------------
async def create_order(client_id, phone, username, from_loc, to_loc, comment):
    row = await fetchrow("""
        INSERT INTO orders (client_id, phone, username, from_loc, to_loc, comment, status)
        VALUES ($1,$2,$3,$4,$5,$6,'waiting')
        RETURNING id
    """, client_id, phone, username, from_loc, to_loc, comment)

    return row["id"]


async def update_order(order_id, status=None, driver_id=None, message_id=None):
    """
    Безопасное обновление:
    - status отдельно
    - driver_id только при назначении
    - message_id только для группы
    """

    await execute("""
        UPDATE orders
        SET
            status = COALESCE($1, status),
            driver_id = COALESCE($2, driver_id),
            message_id = COALESCE($3, message_id)
        WHERE id = $4
    """, status, driver_id, message_id, order_id)


async def get_order(order_id):
    return await fetchrow(
        "SELECT * FROM orders WHERE id=$1",
        order_id
    )


async def delete_order(order_id):
    await execute(
        "DELETE FROM orders WHERE id=$1",
        order_id
    )


# ---------------- DRIVERS ----------------
async def get_driver(user_id):
    return await fetchrow(
        "SELECT * FROM drivers WHERE user_id=$1",
        user_id
    )


# ---------------- NEW (ОЧЕНЬ ВАЖНО) ----------------
async def get_active_order(client_id: int):
    """
    Берёт только активный заказ пользователя
    (убирает необходимость user_active_order)
    """
    return await fetchrow("""
        SELECT *
        FROM orders
        WHERE client_id=$1
          AND status IN ('waiting','taken','arrived')
        ORDER BY id DESC
        LIMIT 1
    """, client_id)
