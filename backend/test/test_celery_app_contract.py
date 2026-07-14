from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_celery_app_is_named_for_diskpulse():
    sources = [
        BACKEND_ROOT / "celery_worker.py",
        BACKEND_ROOT / "celery_tasks" / "tasks" / "storages.py",
        BACKEND_ROOT / "celery_tasks" / "tasks" / "large_files.py",
        BACKEND_ROOT / "scripts" / "start.sh",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in sources)

    assert "diskpulse_app = Celery(" in source
    assert "lsf_app" not in source
    assert "-A celery_worker:diskpulse_app" in source
