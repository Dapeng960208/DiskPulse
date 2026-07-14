# -*- coding: utf-8 -*-


def resolve_group_storage_target(group):
    """Resolve a Group's single storage target and its owning resources."""
    if group.volume_id is not None:
        target_type = "volume"
        target = group.volume
        volume = target
    elif group.qtree_id is not None:
        target_type = "qtree"
        target = group.qtree
        volume = target.volume if target is not None else None
    else:
        target_type = None
        target = None
        volume = None

    return {
        "target_type": target_type,
        "target": target,
        "volume": volume,
        "storage_cluster": group.storage_cluster,
    }
