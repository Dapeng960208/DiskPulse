# -*- coding: utf-8 -*-


def test_main_app_exposes_project_membership_crud_routes():
    from main import app

    methods_by_path = {}
    for route in app.routes:
        methods_by_path.setdefault(route.path, set()).update(route.methods or set())

    path = "/storage-pulse/api/projects/{project_id}/members"
    member_path = "/storage-pulse/api/projects/{project_id}/members/{user_id}"
    assert {"GET", "POST"} <= methods_by_path[path]
    assert {"PATCH", "DELETE"} <= methods_by_path[member_path]
