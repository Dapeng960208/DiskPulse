# StorageCluster 数据库迁移文档

## 概述

本文档描述了为支持多存储集群功能所需的数据库迁移步骤。

## 迁移内容

### PostgreSQL 迁移

#### 1. 新增 storage_clusters 表

```sql
CREATE TABLE storage_clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    storage_host VARCHAR(255) NOT NULL,
    storage_type VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    "limit" FLOAT,
    used FLOAT,
    use_ratio FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_storage_clusters_updated_at ON storage_clusters(updated_at);
```

#### 2. 修改 aggregates 表

```sql
ALTER TABLE aggregates ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_aggregates_storage_cluster_id ON aggregates(storage_cluster_id);
```

#### 3. 修改 volumes 表

```sql
ALTER TABLE volumes ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_volumes_storage_cluster_id ON volumes(storage_cluster_id);
```

#### 4. 修改 qtrees 表

```sql
ALTER TABLE qtrees ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_qtrees_storage_cluster_id ON qtrees(storage_cluster_id);
```

#### 5. 修改 storage_usages 表

```sql
ALTER TABLE storage_usages ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_storage_usages_storage_cluster_id ON storage_usages(storage_cluster_id);
```

### QuestDB 迁移

#### 1. 新增 storage_cluster_storage_usages 表

```sql
CREATE TABLE storage_cluster_storage_usages (
    storage_cluster_id SYMBOL,
    used DOUBLE,
    use_ratio DOUBLE,
    updated_at TIMESTAMP
) TIMESTAMP(updated_at) PARTITION BY DAY WAL;
```

#### 2. 修改 aggregate_storage_usages 表（添加 storage_cluster_id 字段）

QuestDB 不支持直接 ALTER TABLE 添加列，需要重建表：

```sql
-- 备份旧数据
CREATE TABLE aggregate_storage_usages_backup AS (
    SELECT * FROM aggregate_storage_usages
) TIMESTAMP(updated_at) PARTITION BY DAY WAL;

-- 删除旧表
DROP TABLE aggregate_storage_usages;

-- 创建新表（含 storage_cluster_id）
CREATE TABLE aggregate_storage_usages (
    storage_cluster_id SYMBOL,
    aggregate_id SYMBOL,
    used DOUBLE,
    used_ratio DOUBLE,
    updated_at TIMESTAMP
) TIMESTAMP(updated_at) PARTITION BY DAY WAL;

-- 恢复旧数据（storage_cluster_id 为 NULL）
INSERT INTO aggregate_storage_usages (aggregate_id, used, used_ratio, updated_at)
SELECT aggregate_id, used, used_ratio, updated_at FROM aggregate_storage_usages_backup;
```

## 数据迁移（现有数据关联默认集群）

如果系统中已有数据，需要先创建一个默认集群，然后将现有数据关联到该集群：

```sql
-- 1. 插入默认集群（根据实际情况修改 storage_host 和 storage_type）
INSERT INTO storage_clusters (name, storage_host, storage_type, description, is_active)
VALUES ('Default-Cluster', '192.168.1.100', 'netapp', '默认存储集群（迁移用）', TRUE);

-- 获取默认集群 ID（通常为 1）
-- 假设 id = 1

-- 2. 更新 aggregates 表
UPDATE aggregates SET storage_cluster_id = 1 WHERE storage_cluster_id IS NULL;

-- 3. 更新 volumes 表
UPDATE volumes SET storage_cluster_id = 1 WHERE storage_cluster_id IS NULL;

-- 4. 更新 qtrees 表
UPDATE qtrees SET storage_cluster_id = 1 WHERE storage_cluster_id IS NULL;

-- 5. 更新 storage_usages 表
UPDATE storage_usages SET storage_cluster_id = 1 WHERE storage_cluster_id IS NULL;
```

## 回滚方案

如果迁移失败，可以执行以下回滚操作：

```sql
-- 删除新增列
ALTER TABLE aggregates DROP COLUMN storage_cluster_id;
ALTER TABLE volumes DROP COLUMN storage_cluster_id;
ALTER TABLE qtrees DROP COLUMN storage_cluster_id;
ALTER TABLE storage_usages DROP COLUMN storage_cluster_id;

-- 删除新表
DROP TABLE IF EXISTS storage_clusters;
```

## 注意事项

1. **执行顺序**：必须先创建 `storage_clusters` 表，再修改其他表添加外键
2. **低峰期执行**：建议在业务低峰期执行迁移，避免影响正常使用
3. **备份数据**：迁移前务必备份数据库
4. **QuestDB 限制**：QuestDB 不支持 ALTER TABLE 添加列，需要重建表
5. **应用重启**：迁移完成后需要重启应用服务

## 验证迁移

```sql
-- 验证 storage_clusters 表
SELECT COUNT(*) FROM storage_clusters;

-- 验证关联字段
SELECT COUNT(*) FROM aggregates WHERE storage_cluster_id IS NOT NULL;
SELECT COUNT(*) FROM volumes WHERE storage_cluster_id IS NOT NULL;
SELECT COUNT(*) FROM qtrees WHERE storage_cluster_id IS NOT NULL;
SELECT COUNT(*) FROM storage_usages WHERE storage_cluster_id IS NOT NULL;
```
