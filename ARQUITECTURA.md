# Arquitectura — ApoloVibes

> Documento de referencia. Ultima actualizacion: 2026-09-13

---

## 1. Contexto

Sistema de gestion y venta de productos impresos en 3D, con modulo de disenos
personalizados asistido por un LLM. **3 personas, plazo de 4 meses.**

La arquitectura se compone de tres servicios:

- **Gateway Flask** (`gateway/`, publico `:3000`): autenticacion JWT, proxy reverso, rate limiting, CORS, RBAC.
- **Backend Flask** (`app/`, interno `:8000`): logica de negocio, confia en headers `X-User-Id`/`X-User-Rol` inyectados por el gateway.
- **Frontend React** (`ApoloVibes-frontend/`, Vite `:5173`): proxya `/api` al gateway `:3000`.

Oracle Autonomous DB (oracledb thin, wallet) para datos de produccion.
PostgreSQL 16 (docker-compose) solo para tests en `print3d_test`.

---

## 2. Stack tecnologico

| Capa                  | Tecnologia                          | Justificacion |
|-----------------------|-------------------------------------|---------------|
| Framework             | Flask 3.1.3                         | Ya elegido por el equipo; liviano y suficiente. |
| ORM                   | SQLAlchemy 2.0 + Flask-SQLAlchemy   | Maduro, con migraciones (Flask-Migrate/Alembic). |
| Migraciones           | Alembic                             | Evolucion controlada del esquema. |
| Validacion            | Pydantic 2.13                       | Schemas de entrada/salida y validacion de DTOs. |
| JWT Auth              | Flask-JWT-Extended                  | Autenticacion con tokens. |
| Hash de contrasenas   | passlib + bcrypt                    | Listo para usar en capa auth. |
| Tareas async          | Celery 5.5 + Redis 8.1              | Generacion 3D asincrona (polling). |
| Rate limiting         | Flask-Limiter                       | Limites por endpoint, incluido el del LLM. |
| Proxy HTTP            | httpx                               | Proxy reverso del gateway al backend interno. |
| CORS                  | Flask-Cors                          | Origenes configurables via `CORS_ORIGINS`. |
| BD produccion         | Oracle Autonomous DB (oracledb thin)| Persistencia relacional con wallet. |
| BD tests              | PostgreSQL 16 (docker-compose)      | Tests de integracion en `print3d_test`. |
| Server produccion     | gunicorn                            | WSGI de produccion. |
| Testing               | pytest + pytest-flask               | Tests unitarios y de integracion. |

---

## 3. Arquitectura objetivo

**Gateway + Backend separados.** El gateway es el unico punto de entrada publico.
El backend solo se comunica con el gateway y NUNCA se expone directamente.

```
gateway/              :3000 (publico)         app/                :8000 (interno)
├── auth JWT              ──────────────────►  ├── logica de negocio
├── proxy /api/*          ──────────────────►  ├── headers X-User-Id / X-User-Rol
├── rate limiting         ──────────────────►  └── NUNCA expuesto directamente
├── CORS
└── RBAC
```

### 3.1 Frontera de confianza

El **gateway** (`:3000`) es el unico servicio expuesto publicamente.
El **backend** (`:8000`) es interno y solo recibe requests del gateway.
NUNCA exponer `app/` directamente al exterior.

El backend confia ciegamente en los headers `X-User-Id` y `X-User-Rol`
inyectados por el gateway. Si el backend recibe un request sin esos headers,
debe rechazarlo.

### 3.2 Reglas de dependencia (obligatorias)

1. `api` depende de `application` y `domain`. **Nunca** de `infrastructure`
   directamente.
2. `application` depende solo de `domain`. Llamada a infraestructura via
   **interfaces** (inyeccion de dependencias).
3. `domain` no depende de nada externo (sin SQLAlchemy, sin Flask).
4. `infrastructure` implementa las interfaces de `domain`.
5. Los modulos de `application` **no se importan entre si** (RNF-08).
6. El gateway NO depende del backend. Solo le pasa headers HTTP.

---

## 4. Modulos de la capa de aplicacion

Los casos de uso se agrupan en 4 modulos autocontenidos:

| Modulo                 | Responsabilidad |
|------------------------|-----------------|
| `catalogo_stock`       | CRUD de productos y categorias. |
| `pedidos_pagos`        | Creacion/consulta de pedidos; procesamiento de pago (TUU / Pago Online de Haulmer). |
| `disenos_personalizados` | Solicitudes de cotizacion, aprobacion/rechazo, **sanitizacion de inputs** anti prompt-injection. |
| `asistente_llm`        | Orquestacion de llamada al LLM para generacion de modelo 3D. |

### 4.1 Modulo auth (gateway)

El gateway implementa autenticacion y autorizacion:

| Endpoint                | Metodo | Descripcion |
|-------------------------|--------|-------------|
| `/api/auth/login`       | POST   | Login con email/password, retorna JWT access (15 min) y cookie HttpOnly `refresh_token` (7 dias). |
| `/api/auth/refresh`     | POST   | Renovacion de access token via cookie refresh, con rotacion y deteccion de reuso. |
| `/api/auth/logout`      | POST   | Invalidacion del refresh token y limpieza de cookie. |
| `/api/auth/me`          | GET    | Retorna el usuario autenticado a partir del JWT. |

---

## 5. Entidades de dominio

Modelo entidad-relacion ya definido (no se altera):

`Usuario`, `Categoria`, `Producto`, `Pedido`, `DetallePedido`, `Pago`,
`SolicitudDiseno`, `LogAuditoria`, `Notificacion`.

Las entidades viven en `domain/entities/` como clases puras. Los modelos ORM
viven en `infrastructure/database/models/` y mapean a las mismas tablas.

---

## 6. Contratos API (impuestos por el frontend)

Base URL en desarrollo: **http://localhost:3000/api**

Todos los endpoints (excepto auth) se proxean al backend interno via el gateway.

```
# --- Auth (resueltos por el gateway) ---
POST   /api/auth/login                 # body: { email, password } → { access_token, user }
POST   /api/auth/refresh               # cookie refresh_token → { access_token }
POST   /api/auth/logout                # invalida cookie y token
GET    /api/auth/me                    # retorna usuario autenticado

# --- Proxeados al backend interno (:8000) ---
GET    /api/productos                  # catalogo publico
GET    /api/categorias

POST   /api/pedidos
GET    /api/pedidos/:id

POST   /api/pago/crear                 # body: { items, entrega, cliente } → { url }
GET    /api/pago/retorno               # TUU redirige aquí con los parámetros x_*
POST   /api/pago/confirmar             # body: parámetros x_* (+ x_signature)
POST   /api/pago/callback              # notificación server-to-server de TUU (form-urlencoded)

POST   /api/cotizaciones               # multipart: nombre, email, telefono,
                                       #   material, descripcion, imagen, modeloUrl
GET    /api/cotizaciones               # admin
PATCH  /api/cotizaciones/:id           # { estado: aprobada, precio }

POST   /api/ai/image-to-3d             # multipart: imagen → { taskId }
GET    /api/ai/image-to-3d/:taskId     # { status, modelUrl, error } (polling)
```

Formato de error acordado: **`{ mensaje: string }`**.

Endpoint del LLM: **rate limiting especifico e independiente**
(RNF-02) y el minimo numero de campos de entrada permitidos, validados y
sanitizados antes de llegar al LLM (RNF-05).

---

## 7. Requisitos no funcionales -> implementacion

| RNF | Implementacion |
|-----|----------------|
| RNF-02 · Rate limit en LLM | Blueprint `llm_routes.py` con Flask-Limiter configurado por separado. |
| RNF-02 · Rate limit en gateway | Flask-Limiter en el gateway: 5/min login, 10/min refresh, por IP. |
| RNF-05 · Sanitizacion anti prompt-injection | `application/disenos_personalizados/sanitizar_input.py` y `asistente_llm/validar_prompt.py`: whitelist de campos, strip de caracteres peligrosos, longitud maxima, prompt del sistema fijo. |
| RNF-06 · Log de acciones sensibles | Decorador `api/middleware/audit_logger.py` aplicado a endpoints sensibles; persiste en `LogAuditoria`. |
| RNF-08 · Modulos independientes | Regla 5 de la seccion 3.2; cada modulo testeable de forma aislada. |
| Hash de contrasenas | `auth` usa passlib/bcrypt; nunca texto plano. JWT con `Flask-JWT-Extended`. |
| Cookie Secure | Configurable via `GATEWAY_COOKIE_SECURE` (default `true`; en dev con http -> `0`). |

---

## 8. Estructura de carpetas final

```
ApoloVibes/
├── docker-compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── ARQUITECTURA.md                      # copia de docs/ARQUITECTURA.md
├── docs/
│   └── ARQUITECTURA.md                  # fuente principal de este documento
│
├── gateway/                             # API Gateway (:3000, publico)
│   ├── __init__.py
│   ├── main.py                          # punto de entrada Flask
│   ├── config.py                        # configuracion del gateway
│   ├── domain/
│   │   ├── __init__.py
│   │   └── seguridad.py                 # hashing, verificacion de tokens
│   ├── application/
│   │   ├── __init__.py
│   │   └── auth.py                      # casos de uso de autenticacion
│   ├── api/
│   │   ├── __init__.py
│   │   ├── rate_limit.py                # configuracion de Flask-Limiter
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth_routes.py           # /api/auth/*
│   │       ├── proxy_routes.py          # proxy reverso a backend
│   │       └── health_routes.py         # healthcheck
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── oracle_pool.py               # pool de conexiones Oracle
│   │   ├── ddl.py                       # DDL inicial de tablas
│   │   ├── proxy.py                     # implementacion del proxy httpx
│   │   ├── repositorios.py              # repositorio de usuarios/tokens en Oracle
│   │   └── token_service.py             # creacion/verificacion de JWT
│   └── requirements.txt
│
├── app/                                 # Backend interno (:8000)
│   ├── __init__.py                      # factory: create_app()
│   ├── config.py                        # Config por entorno
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
│   ├── migrations/                       # Alembic
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
│
└── ApoloVibes-frontend/                 # React + Vite (:5173)
```

---

## 9. Cambios aplicados al esqueleto anterior

| Antes                  | Despues                                 | Motivo |
|------------------------|-----------------------------------------|--------|
| Backend monolitico en `:4000` | Gateway `:3000` + Backend interno `:8000` | Separacion de responsabilidades: auth/gateway vs. logica de negocio. |
| `app.py` (Hello World) | `__init__.py` factory pattern + `config.py` | Punto de entrada limpio. |
| Auth hardcodeada en backend | Auth en gateway con JWT + Oracle | Tokens en base de datos, refresh con rotacion. |
| `api/` (vacio)         | `api/routes/` + `api/middleware/`       | Separar HTTP de logica. |
| `models/` (vacio)      | `domain/entities/` + `infrastructure/database/models/` | Dominio puro vs. ORM. |
| `schemas/` (vacio)     | `application/common/dto.py` + validacion en `api/` | Pydantic en casos de uso y entrada. |
| `services/` (vacio)    | `application/` (casos de uso)           | Capa de aplicacion formal. |
| `tasks/` (vacio)       | `infrastructure/tasks/` (Celery)        | Tareas = infraestructura. |
| `utils/` (vacio)       | `api/middleware/` + `infrastructure/`   | Funciones con ubicacion especifica. |
| Sin rate limiting      | Flask-Limiter en gateway y backend      | Proteccion contra abuso. |
| Sin proxy              | httpx en gateway proxya a backend       | Backend no expuesto publicamente. |
| `.envexample`          | `.env.example` (raiz)                   | Nombre y ubicacion estandar. |
| `venv/`                | se movera a raiz y se ignora en git     | Eliminado del versionado. |

---

## 10. Pendientes / siguientes pasos

- [x] Aprobacion de estructura y stack
- [x] Auth implementada (JWT + refresh + rotation en gateway)
- [x] Oracle conectado (oracledb thin + wallet)
- [x] Gateway funcional (proxy, CORS, rate limiting, auth)
- [ ] Generacion de archivos base del backend (entidades, interfaces, blueprints, config)
- [ ] Definicion de modelos ORM y primera migracion Alembic
- [ ] Integracion de Flask-Limiter en requisitos del backend
- [ ] Dockerizar backend y gateway
