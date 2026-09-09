Backend ApoloVibes — estructura base configurada.

Arquitectura: monolito modular por capas (Clean Architecture Flask).

Documento de diseño: `docs/ARQUITECTURA.md`

Quickstart
1. python -m venv .venv
2. source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. pip install -r requirements.txt
4. docker compose up -d db
5. flask --app app run --port 4000