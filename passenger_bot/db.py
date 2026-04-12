from shared.database import fetchrow, execute

# ---------------- STATUSES ----------------
ORDER_WAITING = "waiting"
ORDER_TAKEN = "taken"
ORDER_ARRIVED = "arrived"
ORDER_COMPLETED = "completed"
ORDER_CANCELLED = "cancelled"


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
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        RETURNING id
    """, client_id, phone, username, from_loc, to_loc, comment, ORDER_WAITING)

    return row["id"]


# ---------------- 1. SAFE STATUS UPDATE ----------------
async def set_order_status(order_id: int, new_status: str, driver_id: int = None):
    """
    Безопасное изменение статуса + назначение водителя
    """
    await execute("""
        UPDATE orders
        SET
            status = $1,
            driver_id = COALESCE($2, driver_id)
        WHERE id = $3
    """, new_status, driver_id, order_id)


# ---------------- 2. FULL SAFE UPDATE ----------------
async def update_order(order_id, status=None, driver_id=None, message_id=None):
    """
    Гибкое безопасное обновление (ничего не ломает)
    """

    fields = []
    values = []
    idx = 1

    if status is not None:
        fields.append(f"status = ${idx}")
        values.append(status)
        idx += 1

    if driver_id is not None:
        fields.append(f"driver_id = ${idx}")
        values.append(driver_id)
        idx += 1

    if message_id is not None:
        fields.append(f"message_id = ${idx}")
        values.append(message_id)
        idx += 1

    if not fields:
        return

    values.append(order_id)

    await execute(f"""
        UPDATE orders
        SET {", ".join(fields)}
        WHERE id=${idx}
    """, *values)


async def get_order(order_id):
    return await fetchrow(
        "SELECT * FROM orders WHERE id=$1",
        order_id
    )


# ---------------- 3. ACTIVE ORDER ----------------
async def get_active_order(client_id: int):
    return await fetchrow("""
        SELECT *
        FROM orders
        WHERE client_id=$1
          AND status IN ($2, $3, $4)
        ORDER BY id DESC
        LIMIT 1
    """, client_id, ORDER_WAITING, ORDER_TAKEN, ORDER_ARRIVED)


# ---------------- 4. CHECK ACTIVE ----------------
async def has_active_order(client_id: int) -> bool:
    row = await fetchrow("""
        SELECT 1
        FROM orders
        WHERE client_id=$1
          AND status IN ($2, $3, $4)
        LIMIT 1
    """, client_id, ORDER_WAITING, ORDER_TAKEN, ORDER_ARRIVED)

    return row is not None


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
