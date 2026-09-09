"""Configuración de rate limiting.

Flask-Limiter se aplica por blueprint. El endpoint LLM (llm_bp) usa
límites propios e independientes (RNF-02).
"""

LLM_RATE_LIMIT = "5 per minute"
API_GENERAL_RATE_LIMIT = "120 per minute"