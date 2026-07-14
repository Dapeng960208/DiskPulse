ALTER TABLE volume_storage_usages ADD COLUMN IF NOT EXISTS soft_limit DOUBLE;
ALTER TABLE volume_storage_usages ADD COLUMN IF NOT EXISTS soft_use_ratio DOUBLE;

ALTER TABLE qtree_storage_usages ADD COLUMN IF NOT EXISTS soft_limit DOUBLE;
ALTER TABLE qtree_storage_usages ADD COLUMN IF NOT EXISTS soft_use_ratio DOUBLE;

ALTER TABLE project_storage_usages ADD COLUMN IF NOT EXISTS soft_limit DOUBLE;
ALTER TABLE project_storage_usages ADD COLUMN IF NOT EXISTS soft_use_ratio DOUBLE;

ALTER TABLE group_storage_usages ADD COLUMN IF NOT EXISTS soft_limit DOUBLE;
ALTER TABLE group_storage_usages ADD COLUMN IF NOT EXISTS soft_use_ratio DOUBLE;

ALTER TABLE storage_usages ADD COLUMN IF NOT EXISTS soft_limit DOUBLE;
ALTER TABLE storage_usages ADD COLUMN IF NOT EXISTS soft_use_ratio DOUBLE;
