#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NetApp 接口测试脚本
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.netAppClient import NetAppClient

# 手动集成验证连接信息从环境变量读取，避免真实凭据进入代码库。
NETAPP_HOST = os.getenv("NETAPP_HOST")
NETAPP_USERNAME = os.getenv("NETAPP_USERNAME")
NETAPP_PASSWORD = os.getenv("NETAPP_PASSWORD")


def require_netapp_config():
    missing = [
        name
        for name, value in {
            "NETAPP_HOST": NETAPP_HOST,
            "NETAPP_USERNAME": NETAPP_USERNAME,
            "NETAPP_PASSWORD": NETAPP_PASSWORD,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing NetApp environment variables: {', '.join(missing)}")


def connect_netapp():
    """测试 NetApp 连接"""
    require_netapp_config()
    print("正在连接 NetApp...")
    client = NetAppClient(NETAPP_HOST, NETAPP_USERNAME, NETAPP_PASSWORD)
    print("连接成功！\n")
    return client


def show_volumes(client):
    """测试获取卷信息"""
    print("=" * 50)
    print("测试：获取卷信息")
    print("=" * 50)
    volumes = client.get_volumes()
    print(f"共找到 {len(volumes)} 个卷")
    if volumes:
        print(f"第一个卷示例：{volumes[0]}")
    print()
    return volumes

def show_qtrees(client):
    """测试获取 qtree 信息"""
    print("=" * 50)
    print("测试：获取 qtree 信息")
    print("=" * 50)
    qtrees = client.get_qtrees()
    print(f"共找到 {len(qtrees)} 个 qtree")
    if qtrees:
        print(f"第一个 qtree 示例：{qtrees[0]}")
    print()
    return qtrees

def show_aggregates(client):
    """测试获取聚合信息"""
    print("=" * 50)
    print("测试：获取聚合信息")
    print("=" * 50)
    aggregates = client.get_aggregates()
    print(f"共找到 {len(aggregates)} 个聚合")
    if aggregates:
        print(f"第一个聚合示例：{aggregates[0]}")
    print()
    return aggregates

def show_quota(client):
    """测试获取quota信息"""
    print("=" * 50)
    print("测试：获取quota信息")
    print("=" * 50)
    quota_reports = client.get_quota_reports()
    print(f"共找到 {len(quota_reports)} 个聚合")
    if quota_reports:
        print(f"第一个聚合示例：{quota_reports[0]}")
    print()
    return quota_reports

if __name__ == "__main__":
    try:
        # 连接测试
        client = connect_netapp()
        
        # 测试各个接口
        show_volumes(client)
        show_qtrees(client)
        show_aggregates(client)
        show_quota(client=client)
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
