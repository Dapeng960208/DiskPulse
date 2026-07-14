CREATE TABLE IF NOT EXISTS "aggregate_storage_usages" ("storage_cluster_id" SYMBOL, "aggregate_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "group_storage_usages" ("group_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "project_storage_usages" ("project_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "qtree_storage_usages" ("qtree_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "storage_cluster_storage_usages" ("storage_cluster_id" SYMBOL, "used" DOUBLE, "use_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "storage_usages" ("storage_usage_id" SYMBOL, "user_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "file_used" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
CREATE TABLE IF NOT EXISTS "volume_storage_usages" ("volume_id" SYMBOL, "used" DOUBLE, "used_ratio" DOUBLE, "updated_at" TIMESTAMP) TIMESTAMP("updated_at") PARTITION BY DAY WAL;
