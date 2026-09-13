# Propuesta de Arquitectura Backend — ApoloVibes

> Documento de referencia. Última actualización: 2026-09-09

---

## 1. Contexto

Sistema de gestión y venta de productos impresos en 3D, con módulo de diseños
personalizados asistido por un LLM. **3 personas, plazo de 4 meses.**

El frontend (React) queda fuera de este documento; quedan documentados los
**contratos API** que éste ya espera, para que el backend los respete.

---

## 2. Stack tecnológico

| Capa               | Tecnología                          | Justificación |
|--------------------|-------------------------------------|---------------|
| Framework          | Flask 3.1.3                         | Ya elegido por el equipo; liviano y suficiente. |
| ORM                | SQLAlchemy 2.0 + Flask-SQLAlchemy   | Maduro, con migraciones (Flask-Migrate/Alembic). |
| Migraciones        | Alembic                             | Evolución controlada del esquema. |
| Validación         | Pydantic 2.13                       | Schemas de entrada/salida y validación de DTOs. |
| JWT Auth           | Flask-JWT-Extended                  | Autenticación con tokens. |
| Hash de contraseñas | passlib + bcrypt                   | Listo para usar en capa auth. |
| Tareas async       | Celery 5.5 + Redis 8.1              | Generación 3D asíncrona (polling). |
| Rate limiting      | Flask-Limiter (a agregar)           | Límites por endpoint, incluido el del LLM. |
| BD                 | PostgreSQL 16 (docker-compose)      | Persistencia relacional. |
| Server producción  | gunicorn                            | WSGI de producción. |
| Testing            | pytest + pytest-flask               | Tests unitarios y de integración. |

---

## 3. Arquitectura objetivo

**Monolito modular por capas (Clean Architecture).** El código se organiza
primero por capa arquitectónica y dentro de cada capa por módulos de dominio,
manteniendo bajo acoplamiento entre módulos.

```
app/
├── domain/             # Entidades puras + reglas de negocio + interfaces
├── application/        # Casos de uso por módulo (no dependen de framework)
├── api/                # HTTP: blueprints, middleware, validación de entrada
└── infrastructure/     # Implementaciones concretas (DB, LLM, storage, tasks)
```

### 3.1 Reglas de dependencia (obligatorias)

1. `api` depende de `application` y `domain`. **Nunca** de `infrastructure`
   directamente.
2. `application` depende solo de `domain`. Llamada a infraestructura vía
   **interfaces** (inyección de dependencias).
3. `domain` no depende de nada externo (sin SQLAlchemy, sin Flask).
4. `infrastructure` implementa las interfaces de `domain`.
5. Los módulos de `application` **no se importan entre sí** (RNF-08).

---

## 4. Módulos de la capa de aplicación

Los casos de uso se agrupan en 4 módulos autocontenidos:

| Módulo               | Responsabilidad |
|----------------------|-----------------|
| `catalogo_stock`     | CRUD de productos y categorías. |
| `pedidos_pagos`      | Creación/consulta de pedidos; procesamiento de pago (Transbank Webpay Plus). |
| `disenos_personalizados` | Solicitudes de cotización, aprobación/rechazo, **sanitización de inputs** anti prompt-injection. |
| `asistente_llm`      | Orquestación de llamada al LLM para generación de modelo 3D. |

---

## 5. Entidades de dominio

Modelo entidad-relación ya definido (no se altera):

`Usuario`, `Categoria`, `Producto`, `Pedido`, `DetallePedido`, `Pago`,
`SolicitudDiseno`, `LogAuditoria`, `Notificacion`.

Las entidades viven en `domain/entities/` como clases puras. Los modelos ORM
viven en `infrastructure/database/models/` y mapean a las mismas tablas.

> **Nota de desviación (2026-09-13):** la entidad `Producto` agregó dos
> columnas a `productos` para almacenar la imagen como BLOB dentro de la BD:
> `imagen_bytes` (BLOB) y `imagen_content_type` (VARCHAR2(50)). La columna
> `imagen` sigue existiendo pero ahora apunta a la URL del endpoint
> `GET /api/productos/<id>/imagen` que sirve esos bytes. La migración se hace
> manualmente (`migrar_imagen_blob.py`) y el alta vía `agregar_producto.py`,
> ambos fuera de git.

---

## 6. Contratos API (impuestos por el frontend)

Base URL en desarrollo: **http://localhost:4000/api**

```
POST   /api/auth/login                 # devuelve JWT
POST   /api/auth/register
GET    /api/auth/me

GET    /api/productos                  # catálogo público
GET    /api/productos/:id              # detalle público
GET    /api/productos/:id/imagen       # imagen en BLOB (content-type real)
GET    /api/categorias

POST   /api/pedidos
GET    /api/pedidos/:id

POST   /api/pago/crear                 # body: { items, total, cliente } → { url, token }
POST   /api/pago/confirmar             # body: { token }

POST   /api/cotizaciones               # multipart: nombre, email, telefono,
                                       #   material, descripcion, imagen, modeloUrl
GET    /api/cotizaciones               # admin
PATCH  /api/cotizaciones/:id           # { estado: aprobada, precio }

POST   /api/ai/image-to-3d             # multipart: imagen → { taskId }
GET    /api/ai/image-to-3d/:taskId     # { status, modelUrl, error } (polling)
```

Formato de error acordado: **`{ mensaje: string }`**.

Endpoint del LLM: **rate limiting específico e independiente**
(RNF-02) y el mínimo número de campos de entrada permitidos, validados y
sanitizados antes de llegar al LLM (RNF-05).

---

## 7. Requisitos no funcionales → implementación

| RNF | Implementación |
|-----|----------------|
| RNF-02 · Rate limit en LLM | Blueprint `llm_routes.py` con Flask-Limiter configurado por separado. |
| RNF-05 · Sanitización anti prompt-injection | `application/disenos_personalizados/sanitizar_input.py` y `asistente_llm/validar_prompt.py`: whitelist de campos, strip de caracteres peligrosos, longitud máxima, prompt del sistema fijo. |
| RNF-06 · Log de acciones sensibles | Decorador `api/middleware/audit_logger.py` aplicado a endpoints sensibles; persiste en `LogAuditoria`. |
| RNF-08 · Módulos independientes | Regla 5 de la sección 3.1; cada módulo testeable de forma aislada. |
| Hash de contraseñas | `auth` usa passlib/bcrypt; nunca texto plano. JWT con `Flask-JWT-Extended`. |

---

## 8. Estructura de carpetas final

```
ApoloVibes/
├── docker-compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── docs/
│   └── ARQUITECTURA.md                # ← este documento
│
├── app/
│   ├── __init__.py                    # factory: create_app()
│   ├── config.py                      # Config por entorno
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── usuario.py
│   │   │   ├── categoria.py
│   │   │   ├── producto.py
│   │   │   ├── pedido.py
│   │   │   ├── detalle_pedido.py
│   │   │   ├── pago.py
│   │   │   ├── solicitud_diseno.py
│   │   │   ├── log_auditoria.py
│   │   │   └── notificacion.py
│   │   └── interfaces/
│   │       ├── __init__.py
│   │       ├── repository_base.py
│   │       ├── uow.py
│   │       └── repositories.py
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── common/
│   │   │   ├── __init__.py
│   │   │   └── dto.py
│   │   ├── catalogo_stock/
│   │   │   ├── __init__.py
│   │   │   ├── gestionar_producto.py
│   │   │   └── gestionar_categoria.py
│   │   ├── pedidos_pagos/
│   │   │   ├── __init__.py
│   │   │   ├── crear_pedido.py
│   │   │   ├── consultar_pedido.py
│   │   │   └── procesar_pago.py
│   │   ├── disenos_personalizados/
│   │   │   ├── __init__.py
│   │   │   ├── crear_solicitud.py
│   │   │   ├── evaluar_solicitud.py
│   │   │   └── sanitizar_input.py
│   │   └── asistente_llm/
│   │       ├── __init__.py
│   │       ├── generar_modelo_3d.py
│   │       └── validar_prompt.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── error_handler.py
│   │   │   └── audit_logger.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth_routes.py
│   │       ├── catalogo_routes.py
│   │       ├── pedido_routes.py
│   │       ├── diseno_routes.py
│   │       └── llm_routes.py
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── usuario_model.py
│   │   │       ├── categoria_model.py
│   │   │       ├── producto_model.py
│   │   │       ├── pedido_model.py
│   │   │       ├── detalle_pedido_model.py
│   │   │       ├── pago_model.py
│   │   │       ├── solicitud_diseno_model.py
│   │   │       ├── log_auditoria_model.py
│   │   │       └── notificacion_model.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── repository_base.py
│   │   │   ├── usuario_repository.py
│   │   │   ├── producto_repository.py
│   │   │   ├── pedido_repository.py
│   │   │   ├── pago_repository.py
│   │   │   ├── solicitud_diseno_repository.py
│   │   │   └── notificacion_repository.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py
│   │   │   └── prompt_builder.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   └── file_storage.py
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       └── llm_tasks.py
│   │
│   ├── migrations/                   # Alembic
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── uploads/
│   │   ├── cotizaciones/
│   │   └── modelos3d/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── domain/
│       │   └── application/
│       └── integration/
│           ├── api/
│           └── repositories/
```

---

## 9. Cambios aplicados al esqueleto anterior

| Antes (app/)         | Después (app/)                          | Motivo |
|----------------------|-----------------------------------------|--------|
| `app.py` (Hello World) | `__init__.py` factory pattern + `config.py` | Punto de entrada limpio. |
| `api/` (vacío)       | `api/routes/` + `api/middleware/`       | Separar HTTP de lógica. |
| `models/` (vacío)    | `domain/entities/` + `infrastructure/database/models/` | Dominio puro vs. ORM. |
| `schemas/` (vacío)   | `application/common/dto.py` + validación en `api/` | Pydantic en casos de uso y entrada. |
| `services/` (vacío)  | `application/` (casos de uso)           | Capa de aplicación formal. |
| `tasks/` (vacío)     | `infrastructure/tasks/` (Celery)        | Tareas = infraestructura. |
| `utils/` (vacío)     | `api/middleware/` + `infrastructure/`   | Funciones con ubicación específica. |
| `.envexample`        | `.env.example` (raíz)                   | Nombre y ubicación estándar. |
| `venv/`              | se moverá a raíz y se ignora en git     | Eliminado del versionado. |

---

## 10. Pendientes / siguientes pasos

- [x] Aprobación de estructura y stack
- [ ] Generación de archivos base (entidades, interfaces, blueprints, config)
- [ ] Definición de modelos ORM y primera migración Alembic
- [ ] Implementación de auth (JWT + bcrypt) end-to-end
- [ ] Integración de Flask-Limiter en requisitos
- [ ] Dockerizar el backend (opcional, fase 2)