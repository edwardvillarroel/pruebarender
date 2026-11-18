from app.infrastructure.tasks.celery_app import celery_app


@celery_app.task(name="llm.generar_modelo_3d")
def generar_modelo_3d_tarea(solicitud_id: str, imagen_path: str) -> dict:
    raise NotImplementedError