Por ahora solo está la base del entorno. **Flask y PostgreSQL no están conectados** ni hay modelos/tablas.

Archivos
- `requirements.txt` — dependencias agrupadas por función
- `docker-compose.yaml` — PostgreSQL de desarrollo
- `app.py` — servidor Flask mínimo (sin lógica de negocio)

1. Entorno virtual
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt