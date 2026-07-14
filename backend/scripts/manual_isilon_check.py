#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用数据库中已配置的 Isilon 集群执行只读 Quota 检查。"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from appConfig import base_config
from database import SessionLocal
from models import StorageCluster
from utils.isilonClient import IsilonClient


def load_isilon_config(db, cluster_name):
    row = db.execute(
        select(
            StorageCluster.name,
            StorageCluster.storage_host.label("host"),
            StorageCluster.storage_port.label("port"),
            StorageCluster.storage_user.label("username"),
            StorageCluster.storage_password.label("password"),
        ).where(
            StorageCluster.name == cluster_name,
            StorageCluster.storage_type == "isilon",
        )
    ).mappings().one_or_none()
    if row is None:
        raise RuntimeError(f"未找到 Isilon 存储集群配置：{cluster_name}")

    config = dict(row)
    missing = [
        key
        for key in ("host", "port", "username", "password")
        if not config[key]
    ]
    if missing:
        raise RuntimeError(f"Isilon 存储集群配置缺少字段：{', '.join(missing)}")
    return config


def fetch_quota_summary(config, *, tls_verify, client_factory=IsilonClient):
    client = client_factory(
        config["host"],
        config["username"],
        config["password"],
        port=config["port"],
        tls_verify=tls_verify,
    )
    try:
        counts = Counter(
            (quota.get("type") or "unknown") for quota in client.get_quotas()
        )
        return {"total": sum(counts.values()), "types": dict(sorted(counts.items()))}
    finally:
        client.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cluster_name", help="storage_clusters 表中的 Isilon 集群名称")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        config = load_isilon_config(db, args.cluster_name)

    summary = fetch_quota_summary(
        config,
        tls_verify=base_config.get("storage.tls_verify", True),
    )
    print(f"集群：{config['name']}")
    print(f"Quota 总数：{summary['total']}")
    for quota_type, count in summary["types"].items():
        print(f"  {quota_type}: {count}")
    return 0 if summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
