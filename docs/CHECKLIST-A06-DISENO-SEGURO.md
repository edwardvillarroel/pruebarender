# Checklist A06:2025 — Diseño Inseguro (Insecure Design)

**Proyecto:** ApoloVibes 3D · **Versión:** 1.0 · **Fecha:** noviembre 2026
**Base:** OWASP Top 10 2025 — A06 Insecure Design + SGSI interno
**Alcance:** gateway público (`gateway/`), backend interno (`app/`), frontend.

Este checklist separa **diseño** de **implementación**: verifica que existan los
controles antes de preguntar si están bien codificados. Se recorre en cada
cambio que toque autenticación, autorización, pagos, pedidos, cupones, stock,
archivos o datos personales.

## Estados

| Estado | Significado |
|---|---|
| ✅ | Implementado y verificable en el repo |
| ⚠️ | Parcial: existe el control pero falta cobertura, automatización o alcance |
| ❌ | Pendiente: el control no existe |
| 🔎 | Verificación externa (panel/proveedor; no verificable desde el repo) |
| ➖ | No aplica al sistema |

---

## 1. Requisitos y gestión de riesgos

| # | Control | Estado | Evidencia / nota | Acción |
|---|---|---|---|---|
| 1.1 | Activos y riesgos de negocio identificados | ✅ | `docs/SGSI-INTERNO-APOLOVIBES3D.md` secciones A y B (Top 5) | Mantener |
| 1.2 | Criticidad definida por flujo (pago, login, datos personales) | ⚠️ | Riesgos globales del SGSI; no hay criticidad por endpoint/flujo | Clasificar flujos en la próxima revisión |
| 1.3 | Requisitos de seguridad por funcionalidad nueva | ❌ | No hay plantilla de requisitos | Usar la sección 4 (historias de abuso) como punto de partida |
| 1.4 | Modelo de amenazas ligero por feature | ❌ | Solo existe el análisis global del SGSI | Hacer uno por épica que toque dinero/auth/datos |
| 1.5 | Recursos para controles (backups, logs, límites) | ⚠️ | Backups y purge definidos (SGSI F); rate limit parcial | Ver 2.7 |

## 2. Diseño seguro (controles verificables)

### 2.1 Frontera de confianza

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.1.1 | Única entrada pública es el gateway; backend escucha solo en loopback | ✅ | `scripts/iniciar_render.sh` (`--bind 127.0.0.1:8000`), `docs/DEPLOY_RENDER_V2NET.md` |
| 2.1.2 | Backend no confía en `X-User-Id`/`X-User-Rol` del cliente | ✅ | `app/api/middleware/auth.py` (`_es_cliente_interno_valido`), `gateway/infrastructure/proxy.py` |
| 2.1.3 | Frontera fail-closed si falta el secreto compartido | ✅ | `INTERNAL_SECRET` vacío ⇒ toda sesión responde 401 (`test_sin_secreto_configurado_es_fail_closed`) |
| 2.1.4 | El gateway valida el JWT antes de inyectar identidad | ✅ | `gateway/api/routes/proxy_routes.py` (`verify_jwt_in_request`, `get_jwt`) |

### 2.2 Autorización

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.2.1 | Guard de sesión y de rol declarativos | ✅ | `requiere_sesion()`, `rol_requerido()` en `app/api/middleware/auth.py` |
| 2.2.2 | Propiedad del recurso verificada (no solo el id de la URL) | ✅ | `app/tests/unit/api/test_pedido_routes_acceso.py` (dueño vs. otro usuario vs. admin) |
| 2.2.3 | Roles acotados en base de datos | ✅ | `CHECK (rol IN ('admin','cliente'))` en `migrations/postgres/schema_completo.sql` |
| 2.2.4 | Rol forzado a `cliente` en registro público | ✅ | Flujo de registro del gateway |

### 2.3 Reglas de negocio

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.3.1 | Precios, totales y descuentos se calculan en servidor | ✅ | `app/application/pedidos_pagos/crear_pedido.py`, `procesar_pago.py` |
| 2.3.2 | Stock validado y descontado de forma atómica | ✅ | `update(...).where(stock >= cantidad)` en `producto_repository.descontar_stock` |
| 2.3.3 | Cupones con uso controlado y liberación al cancelar | ✅ | `app/application/pedidos_pagos/gestionar_pedido_no_pagado.py` (`_liberar_cupon`) |
| 2.3.4 | Idempotencia en emisión de DTE | ✅ | Clave `dte-<pedido_id>` en `app/application/facturacion/emitir_documento_tributario.py` |
| 2.3.5 | Referencia de pago no adivinable / ligada al pedido | ✅ | `app/application/common/referencias.py` (base62 del `pedido.id`) |
| 2.3.6 | Confirmación de pago solo con firma válida | ✅ | `TuuCliente.verificar_firma` (fail-closed sin key) + callback en `pedido_routes.py` |

### 2.4 Abuso y límites

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.4.1 | Rate limit en login / refresh / MFA | ✅ | `gateway/api/routes/auth_routes.py` (20/min, 10/min, 5/min) |
| 2.4.2 | CAPTCHA a partir del 3.er fallo de login | ✅ | `gateway/application/auth.py` + `auth_routes.py` |
| 2.4.3 | Bloqueo temporal por fuerza bruta (password y MFA) | ✅ | `UMBRAL_FALLOS_PASSWORD = 5`, `UMBRAL_FALLOS_MFA = 3` |
| 2.4.4 | Límite en el resto de la API (catch-all del proxy) | ❌ | El proxy no tiene límite por ruta; solo auth lo tiene |
| 2.4.5 | Límite de tamaño/tipo de archivos subidos | ✅ | `app/infrastructure/imagenes/validador_imagen_segura.py`, `app/config.py` |
| 2.4.6 | Límite de ítems por carrito/pedido | 🔎 | Verificar si el frontend o el backend acotan cantidad; no hay constante explícita |

### 2.5 Errores y estados

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.5.1 | Contrato de error uniforme `{ "mensaje" }` | ✅ | `app/api/middleware/error_handler.py`, rutas de cupón/diseño |
| 2.5.2 | Error no controlado devuelve 500 JSON sin stacktrace | ✅ | `@app.errorhandler(Exception)` + tests de `test_error_handler.py` |
| 2.5.3 | Operaciones sensibles auditadas | ✅ | `@auditar` en pedidos/usuarios, persistencia en `logs_auditoria` |
| 2.5.4 | Estados de pedido con transiciones válidas | ✅ | `app/application/pedidos_pagos/cambiar_estado_pedido.py` + tests |

### 2.6 Datos y secretos

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 2.6.1 | Contraseñas con hash lento (bcrypt) | ✅ | `passlib[bcrypt]`, `bcrypt` en `requirements.txt` |
| 2.6.2 | MFA/TOTP disponible para el panel | ✅ | `gateway/domain/seguridad.py`, `auth.py` |
| 2.6.3 | Secretos fuera del código | ✅ | `TUU_SECRET_KEY` sin default embebido (`app/config.py`); `INTERNAL_SECRET` por entorno |
| 2.6.4 | Secretos históricos fuera de git | ⚠️ | La key de prueba de TUU quedó en commits anteriores; la real nunca debe estar en el repo |
| 2.6.5 | Cifrado en tránsito (TLS) | 🔎 | Verificar TLS en Render, Supabase, Resend y V2NET |
| 2.6.6 | Archivos de cotización con acceso firmado y expiratorio | ✅ | `firmas_upload.py`, `GET /api/uploads/<path>` |

## 3. Ciclo de vida de desarrollo seguro

| # | Control | Estado | Evidencia / nota |
|---|---|---|---|
| 3.1 | Revisión de diseño antes de implementar features sensibles | ❌ | No hay artefacto de revisión |
| 3.2 | Checklist de seguridad en el PR | ❌ | Usar este documento como base |
| 3.3 | CI obligatorio (tests) antes de mergear | ❌ | No hay CI de tests; solo el cron de purge (`.github/workflows/`) |
| 3.4 | Revisión de dependencias en el PR | ❌ | Ver `CHECKLIST-A08-INTEGRIDAD.md` |
| 3.5 | Pruebas automatizadas de los controles críticos | ⚠️ | Hay unitarios de auth, acceso, errores y auditoría; faltan pruebas negativas de negocio |
| 3.6 | Análisis estático / DAST | ❌ | No hay SAST ni escaneo dinámico |
| 3.7 | Procedimiento de incidentes | ✅ | `docs/SGSI-INTERNO-APOLOVIBES3D.md` sección D |
| 3.8 | Revisión periódica del diseño | ✅ | SGSI sección E (cada 6 meses / cambio de infra) |

## 4. Historias de abuso (casos negativos esperados)

Cada historia debe tener al menos un test que la cubra:

| # | Historia de abuso | Cobertura |
|---|---|---|
| 4.1 | Cliente B pide el pedido de A por id → 403 | `test_detalle_pedido_de_otro_usuario_es_403` |
| 4.2 | Cliente intenta una acción de admin → 403 | `test_solo_admin_con_rol_cliente_es_403`, tests de usuarios |
| 4.3 | Request directa al backend con `X-User-Id` falso → 401 | `test_sin_secreto_configurado_es_fail_closed` |
| 4.4 | Callback de pago con firma inválida → rechazado | `test_verificar_firma_*` (TUU) |
| 4.5 | Dos compras simultáneas del último ítem → una falla | `descontar_stock` atómico + tests de integración |
| 4.6 | Reutilizar un cupón ya usado → rechazado/liberado | Flujo de cupones |
| 4.7 | Fuerza bruta de password/MFA → bloqueo | `test_*` del gateway/auth |
| 4.8 | Subir archivo malicioso → rechazado | `validador_imagen_segura` |
| 4.9 | Abrir una URL de upload sin firma → 403 | `servir_uploads` |
| 4.10 | Reusar un refresh token rotado → se revoca la sesión | `rotar_refresh` (gateway) |

## 5. Verificación rápida

```bash
# Controles de acceso y frontera interna
python -m pytest app/tests/unit/api/test_auth_middleware.py -q
python -m pytest app/tests/unit/api/test_pedido_routes_acceso.py -q

# Auditoría y errores
python -m pytest app/tests/unit/api/test_audit_logger.py -q
python -m pytest app/tests/unit/api/test_error_handler.py -q

# Integridad de pago
python -m pytest app/tests/unit/infrastructure/pagos/test_tuu_client.py -q

# Suite sin base
python -m pytest app/tests/unit -q
```

## 6. Brechas priorizadas

| Prioridad | Brecha | Dueño | Estado |
|---|---|---|---|
| P1 | CI que ejecute la suite en cada PR (hoy nada impide mergear en rojo) | Desarrollo | ❌ |
| P1 | Modelo de amenazas + historias de abuso por feature sensible | Desarrollo | ❌ |
| P2 | Límite de tasa en el proxy (más allá de auth) | Desarrollo | ❌ |
| P2 | Checklist de seguridad en el PR (usar este doc) | Desarrollo | ❌ |
| P3 | SAST/DAST y dependencias (ver A08) | Desarrollo | ❌ |
| P3 | Criticidad por flujo y límite de ítems de carrito | Desarrollo | ⚠️ |

## 7. Registro de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Noviembre 2026 | Versión inicial: relevamiento OWASP A06 sobre el estado del repo |
