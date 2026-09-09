import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_dev"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    JWT_TOKEN_LOCATION = ["headers"]

    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "glb", "stl"}
    UPLOAD_FOLDER = BASE_DIR / "uploads"

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST", str(BASE_DIR.parent / "ApoloVibes-frontend" / "dist")
    )
    # Prefijo del build de Vite (vite.config.js usa base: "/ApoloVibes3D-Frontend/").
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/ApoloVibes3D-Frontend/")

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_test"
    )


class ProductionConfig(Config):
    DEBUG = False