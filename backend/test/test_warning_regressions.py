# -*- coding: utf-8 -*-
import importlib
import warnings

import pytest
from fastapi import HTTPException, status


SCHEMA_MODULES = (
    "schemas.aggregateSchema",
    "schemas.configSchemas",
    "schemas.largeFileSchema",
    "schemas.projectsSchema",
    "schemas.qtreeSchema",
    "schemas.storageAlertsSchema",
    "schemas.storageBackUpRecordSchema",
    "schemas.storageClusterSchema",
    "schemas.storageUsageSchema",
    "schemas.usersSchema",
    "schemas.volumeSchema",
)


@pytest.mark.parametrize("module_name", ("database", "questdb.database", *SCHEMA_MODULES))
def test_backend_module_reload_has_no_deprecation_warnings(module_name):
    module = importlib.import_module(module_name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(module)

    assert not caught, [f"{warning.category.__name__}: {warning.message}" for warning in caught]


def test_group_filter_validation_uses_current_422_status_without_warning():
    from crud import groupCrud

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(HTTPException) as error:
            groupCrud.get_groups(db=None, volume_id=1, qtree_id=2)

    assert error.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert not [warning for warning in caught if issubclass(warning.category, DeprecationWarning)]
