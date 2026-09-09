from flask import Blueprint, jsonify

from app.api.middleware.rate_limiter import LLM_RATE_LIMIT

llm_bp = Blueprint("llm", __name__)


@llm_bp.post("/ai/image-to-3d")
def iniciar_generacion_modelo():
    # TODO: multipart (imagen) -> { taskId }
    # Rate limiting especifico del LLM (RNF-02).
    raise NotImplementedError


@llm_bp.get("/ai/image-to-3d/<task_id>")
def estado_generacion_modelo(task_id):
    # TODO: { status: processing|completed|failed, modelUrl, error }
    raise NotImplementedError