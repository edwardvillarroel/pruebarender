from celery import Celery


def crear_celery_app() -> Celery:
    celery_app = Celery(
        "apolovibes",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Santiago",
        enable_utc=True,
    )
    celery_app.autodiscover_tasks(["app.infrastructure.tasks"])
    return celery_app


celery_app = crear_celery_app()