#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Isilon OneFS PAPI 接口测试脚本"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.isilonClient import IsilonClient

ISILON_HOST = "10.0.20.81"
ISILON_PORT = 8080
ISILON_USERNAME = "jianpeng.guo"
ISILON_PASSWORD = "n@6jTk#TNfk4Etp9"


def main():
    print("连接 Isilon ...")
    client = IsilonClient(ISILON_HOST, ISILON_USERNAME, ISILON_PASSWORD, port=ISILON_PORT)

    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("测试：获取集群存储统计 (GET /platform/1/cluster/statfs)")
    print("=" * 50)
    stats = client.get_cluster_stats()
    if stats:
        bsize = stats.get('f_bsize', 512)
        total_tb = stats.get('f_blocks', 0) * bsize / 1024 ** 4
        avail_tb = stats.get('f_bavail', 0) * bsize / 1024 ** 4
        used_tb = total_tb - avail_tb
        print(f"  总容量:   {total_tb:.2f} TB")
        print(f"  已使用:   {used_tb:.2f} TB")
        print(f"  可用:     {avail_tb:.2f} TB")
        print(f"  使用率:   {used_tb / total_tb * 100:.1f}%" if total_tb else "  使用率: N/A")
    else:
        print("  未获取到集群统计数据")

    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("测试：获取配额列表 (GET /platform/1/quota/quotas)")
    print("=" * 50)
    quotas = client.get_quotas()
    default_user_quotas = [q for q in quotas if q.get('type') == 'default-user']
    user_quotas = [q for q in quotas if q.get('path') == '/ifs/data/IC/tmpdata/project/dijun']
    dir_quotas  = [q for q in quotas if q.get('type') == 'directory']
    print(f"  共找到 {len(quotas)} 个配额")
    print(f"    user 配额:      {len(user_quotas)} 个")
    print(f"    directory 配额: {len(dir_quotas)} 个")
    print(f"    default_user 配额: {len(dir_quotas)} 个")

    print("\n  前 3 条 user 配额详情:")
    for q in default_user_quotas[:3]:
        print(q)

    print("\n  前  条 user 配额详情:")
    for q in user_quotas:
        persona    = q.get('persona') or {}
        thresholds = q.get('thresholds') or {}
        usage      = q.get('usage') or {}
        hard_bytes = thresholds.get('hard')
        used_bytes = usage.get('logical')
        hard_gb    = round(hard_bytes / 1024 ** 3, 2) if hard_bytes else None
        used_gb    = round(used_bytes / 1024 ** 3, 2) if used_bytes else None
        print(f"    path={q.get('path')}  user={persona.get('name')}  "
              f"used={used_gb} GB  hard={hard_gb} GB {q.get('type')}")

    # if user_quotas:
    #     print(f"\n  第 1 条原始数据:\n{json.dumps(user_quotas[0], indent=4)}")
    #
    # # ------------------------------------------------------------------
    # print("\n" + "=" * 50)
    # print("测试：获取 NFS exports (GET /platform/2/protocols/nfs/exports)")
    # print("=" * 50)
    # exports = client.get_exports()
    # print(f"  共找到 {len(exports)} 个 NFS export")
    # for e in exports[:3]:
    #     print(f"    id={e.get('id')}  paths={e.get('paths')}  "
    #           f"clients={e.get('clients')}")
    #
    # if exports:
    #     print(f"\n  第 1 条原始数据:\n{json.dumps(exports[0], indent=4)}")
    #
    # client.close()
    # print("\n所有测试完成！")


if __name__ == "__main__":
    main()
