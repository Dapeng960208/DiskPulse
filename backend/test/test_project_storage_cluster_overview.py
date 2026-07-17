# -*- coding: utf-8 -*-
from crud import projectsCrud
from models import Group, GroupTag, Project, StorageCluster
from schemas.projectsSchema import ProjectOverview


def test_project_overview_includes_deduplicated_sorted_storage_clusters(db_session):
    project = Project(id=101, name="多集群项目", status=1)
    zhuhai = StorageCluster(
        id=102,
        name="珠海",
        storage_type="isilon",
        storage_host="zhuhai.example.test",
        is_active=True,
    )
    beijing = StorageCluster(
        id=103,
        name="北京",
        storage_type="netapp",
        storage_host="beijing.example.test",
        is_active=True,
    )
    group_tag = GroupTag(id=107, name="测试标签")
    db_session.add_all([
        project,
        zhuhai,
        beijing,
        group_tag,
        Group(id=104, name="项目组 A", project_id=project.id, storage_cluster_id=zhuhai.id, group_tag_id=group_tag.id, enable_monitoring=False),
        Group(id=105, name="项目组 B", project_id=project.id, storage_cluster_id=beijing.id, group_tag_id=group_tag.id, enable_monitoring=False),
        Group(id=106, name="项目组 C", project_id=project.id, storage_cluster_id=zhuhai.id, group_tag_id=group_tag.id, enable_monitoring=False),
    ])
    db_session.commit()

    projects, total = projectsCrud.get_projects(db_session, page=1, size=20)
    overview = next(item for item in projects if item.id == project.id)

    assert total == 1
    assert overview.storage_cluster_types == ["isilon", "netapp"]
    assert overview.storage_clusters == [
        {"id": beijing.id, "name": "北京", "storage_type": "netapp"},
        {"id": zhuhai.id, "name": "珠海", "storage_type": "isilon"},
    ]
    assert ProjectOverview.model_validate(overview).model_dump()["storage_clusters"] == overview.storage_clusters
