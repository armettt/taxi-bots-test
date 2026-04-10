-- Таблицы для ботов

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS drivers (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    phone TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    color TEXT,
    plate TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL,
    phone TEXT NOT NULL,
    username TEXT,
    from_loc TEXT,
    to_loc TEXT,
    comment TEXT,
    status TEXT DEFAULT 'waiting',
    driver_id BIGINT,
    message_id BIGINT
);
