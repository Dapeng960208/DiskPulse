#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NetApp 接口测试脚本
"""
from utils.netAppClient import NetAppClient

# 配置连接信息（请填入实际值）
NETAPP_HOST = "10.8.20.92"
NETAPP_USERNAME = "jianpeng.guo"
NETAPP_PASSWORD = "n@6jTk#TNfk4Etp9"

def test_netapp_connection():
    """测试 NetApp 连接"""
    print("正在连接 NetApp...")
    client = NetAppClient(NETAPP_HOST, NETAPP_USERNAME, NETAPP_PASSWORD)
    print("连接成功！\n")
    return client

def test_get_volumes(client):
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

def test_get_qtrees(client):
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

def test_get_aggregates(client):
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

def test_get_quota(client):
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
        client = test_netapp_connection()
        
        # 测试各个接口
        test_get_volumes(client)
        test_get_qtrees(client)
        test_get_aggregates(client)
        test_get_quota(client=client)
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
