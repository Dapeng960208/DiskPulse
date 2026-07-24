# -*- coding: utf-8 -*-
"""Production FastAPI application route contract tests."""


def test_production_app_mounts_storage_backup_and_large_file_routes():
    from main import app

    paths = {route.path for route in app.routes}

    assert "/storage-pulse/api/storage-back-up-records/" in paths
    assert "/storage-pulse/api/large-files/" in paths
