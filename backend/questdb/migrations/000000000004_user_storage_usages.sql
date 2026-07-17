CREATE TABLE IF NOT EXISTS "user_storage_usages" (
    "user_id" SYMBOL,
    "limit" DOUBLE,
    "soft_limit" DOUBLE,
    "used" DOUBLE,
    "use_ratio" DOUBLE,
    "soft_use_ratio" DOUBLE,
    "file_used" DOUBLE,
    "updated_at" TIMESTAMP
) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
