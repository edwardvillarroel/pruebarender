# Checklist A08:2025 — Fallas de Integridad de Software y Datos

**Proyecto:** ApoloVibes 3D · **Versión:** 1.0 · **Fecha:** noviembre 2026
**Base:** OWASP Top 10 2025 — A08 Software or Data Integrity Failures
**Alcance:** dependencias Python, frontend, CI/CD (GitHub Actions), pipeline de
deploy (Render), datos en tránsito/persistencia y controles de firma.
**Complemento:** `docs/CHECKLIST-A06-DISENO-SEGURO.md` (controles de diseño).

El objetivo es que **nada entre al sistema sin verificación**: ni una
dependencia, ni un artefacto de build, ni un callback de pago, ni una fila de la
base tratada como confiable sin restricciones.

## Estados

| Estado | Significado |
|---|---|
| ✅ | Implementado y verificable en el repo |
| ⚠️ | Parcial: existe el control pero falta automatización o alcance |
| ❌ | Pendiente |
| 🔎 | Verificación externa (otro repo/panel; no verificable desde acá) |
| ➖ | No aplica |

---

## 1. Dependencias y cadena de suministro

| # | Control | Estado | Evidencia / nota | Acción |
|---|---|---|---|---|
| 1.1 | Dependencias Python con versión fija (`==`) | ✅ | `requirements.txt` y `gateway/requirements.txt` (actualizado en la remediación A03) | Mantener |
| 1.2 | Instalación con hashes (`--require-hashes`) | ❌ | `pip install -r requirements.txt` sin hashes; un índice comprometido podría servir otro artefacto | Evaluar `pip-compile --generate-hashes` |
| 1.3 | Lockfile en el frontend | ✅ 🔎 | `ApoloVibes-frontend/package-lock.json`; el frontend de producción vive en otro repo (`../apolovibes-front`) | Verificar lockfile en el repo de producción |
| 1.4 | Sin JavaScript de CDNs de terceros | ✅ | El build solo referencia Google Fonts (CSS); el JS se empaqueta con Vite | Mantener |
| 1.5 | Integridad de recursos de CDN (SRI) | ➖ | Solo se cargan fuentes de Google Fonts; no hay `<script src>` externo | Revisar si se agrega un CDN de JS |
| 1.6 | Escaneo automático de vulnerabilidades | ❌ | No hay `pip-audit`, `npm audit` en CI ni Dependabot | Agregar `pip-audit` + Dependabot |
| 1.7 | Actualización controlada de dependencias | ❌ | Sin Dependabot/Renovate; actualización manual | Definir cadencia (mensual) |
| 1.8 | SBOM / inventario de componentes | ❌ | No se genera | Generar SBOM (CycloneDX) en el build |
| 1.9 | Dependencias declaradas pero no usadas | ⚠️ | `Flask-Migrate`/`Alembic` están en requirements y no se usan (esquema SQL crudo) | Depurar para reducir superficie |

## 2. CI/CD e integridad de artefactos

| # | Control | Estado | Evidencia / nota | Acción |
|---|---|---|---|---|
| 2.1 | Workflows de GitHub Actions | ⚠️ | Solo `.github/workflows/purgar-cotizaciones.yml` (cron semanal); **no hay CI de tests** | Agregar workflow de test/lint en PR |
| 2.2 | Acciones de terceros fijadas por SHA | ✅ ➖ | El único workflow no usa `uses:` (solo `curl`), así que no hay acciones que fijar | Mantener la regla si se agregan |
| 2.3 | Permisos mínimos del `GITHUB_TOKEN` | ⚠️ | No se declara `permissions:`; queda el default del repo | Declarar `permissions: contents: read` en cada workflow |
| 2.4 | Secretos en GitHub Secrets (no en el YAML) | ✅ | `${{ secrets.CRON_SECRET }}` | Mantener |
| 2.5 | Protección de rama / revisión obligatoria | 🔎 | No verificable desde el repo | Confirmar en GitHub (rama `main`) |
| 2.6 | Deploy reproducible y controlado | ⚠️ | Render construye desde el repo con `pip install`; no hay artefacto inmutable ni rollback por digest | Documentar rollback y versión desplegada |
| 2.7 | Firma/verificación de artefactos de build | ❌ | No hay imágenes ni binarios firmados; el deploy es código fuente | Aceptable para el tamaño actual; revisar si se containeriza |
| 2.8 | Integridad del workflow de cron | ✅ | `curl -fsS` con `X-Cron-Secret`; sin `pull_request_target` ni ejecución de código de PR | Mantener |

## 3. Integridad de datos y firmas

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 3.1 | Callback de pago validado con HMAC-SHA256 | ✅ | `TuuCliente.verificar_firma` (`hmac.compare_digest`) |
| 3.2 | Firma de pago fail-closed sin secreto | ✅ | Sin `TUU_SECRET_KEY` no se cobra ni se acepta callback (`test_tuu_client.py`) |
| 3.3 | URLs de archivos privados firmadas y con expiración | ✅ | `app/infrastructure/imagenes/firmas_upload.py` (`?exp=&sig=`, `compare_digest`) |
| 3.4 | JWT de acceso corto + refresh con rotación | ✅ | `gateway/config.py` (15 min) y `gateway/application/auth.py` (`rotar_refresh`) |
| 3.5 | Detección de reuso de refresh token | ✅ | `rotar_refresh`: reuso ⇒ revoca toda la sesión y registra log |
| 3.6 | Idempotencia en emisión de DTE | ✅ | Clave determinista `dte-<pedido_id>` |
| 3.7 | Idempotencia/trazabilidad del pago | ✅ | `x_reference` = base62 del `pedido.id` |
| 3.8 | Restricciones de integridad en la base | ✅ | `CHECK`, `UNIQUE`, `PRIMARY KEY` y `FOREIGN KEY` en `migrations/postgres/schema_completo.sql` |
| 3.9 | Actualización de stock atómica (sin carreras) | ✅ | `UPDATE ... WHERE stock >= cantidad` en `producto_repository.descontar_stock` |
| 3.10 | Esquema reproducible desde cero | ✅ | `migrations/postgres/schema_completo.sql` es la fuente única |
| 3.11 | Migraciones versionadas automáticamente | ⚠️ | SQL crudo manual; no se usa Alembic aunque esté instalado | Documentar orden de migraciones o adoptar Alembic |
| 3.12 | Backups con prueba de restauración | ✅ | `docs/PROCEDIMIENTO-BACKUP-SUPABASE.md`, `docs/REGISTRO-BACKUPS.md` (prueba OK) |
| 3.13 | Logs de auditoría persistentes | ✅ | `logs_auditoria` + `GestionAuditoria` (`@auditar`) |
| 3.14 | Protección anti-manipulación de logs | ⚠️ | No hay hash-chain, WORM ni copia externa de `logs_auditoria` | Evaluar exportación/backup de logs |

## 4. Deserialización

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 4.1 | Solo JSON como formato de entrada | ✅ | `request.get_json()` en las rutas |
| 4.2 | Sin deserialización insegura (`pickle`, `marshal`, `yaml.load`, `eval`, `exec`) | ✅ | Búsqueda en `app/` y `gateway/`: sin usos (el único match de `eval(` es una lista de patrones sospechosos del validador de imágenes) |
| 4.3 | Validación de tipos/campos de payload | ⚠️ | Hay validaciones por endpoint y `pydantic` disponible; no todos los DTO usan un esquema estricto | Unificar validación en los flujos críticos |
| 4.4 | Sin actualizaciones automáticas de la aplicación | ➖ | No existe mecanismo de auto-update | — |

## 5. Secretos y configuración

| # | Control | Estado | Evidencia |
|---|---|---|---|
| 5.1 | Secretos por entorno, nunca en el código | ✅ | `TUU_SECRET_KEY` sin default; `INTERNAL_SECRET`, `SECRET_KEY`, `CRON_SECRET` por entorno |
| 5.2 | Variables generadas en el deploy | ✅ | `render.yaml` (`generateValue` para `SECRET_KEY`, `GATEWAY_SECRET_KEY`, `INTERNAL_SECRET`) |
| 5.3 | Secretos de prueba fuera del repo | ⚠️ | La key de prueba de TUU estuvo commiteada; confirmar que nunca fue la de producción y evaluar limpieza del historial |
| 5.4 | Rotación de secretos documentada | ❌ | No hay procedimiento de rotación (salvo backups/cron) | Documentar rotación de claves |

## 6. Verificación rápida

```bash
# Firma de pagos (integridad de callback)
python -m pytest app/tests/unit/infrastructure/pagos/test_tuu_client.py -q

# URLs firmadas de archivos
python -m pytest app/tests/unit/infrastructure/imagenes/test_firmas_upload.py -q

# Idempotencia / facturación
python -m pytest app/tests/unit/application/facturacion -q

# Búsqueda de deserialización insegura
rg "pickle|marshal|yaml\.load|eval\(|exec\(" app gateway
```

## 7. Brechas priorizadas

| Prioridad | Brecha | Acción concreta |
|---|---|---|
| P1 | Sin CI de tests en PR | Workflow `pytest app/tests/unit` + `npm run build` en cada PR |
| P1 | Sin escaneo de dependencias | `pip-audit -r requirements.txt` en CI + Dependabot |
| P2 | Sin hashes en dependencias Python | `pip-compile --generate-hashes` o `uv lock` |
| P2 | Sin `permissions:` en workflows | `permissions: contents: read` |
| P2 | Sin SBOM | Generar CycloneDX en el build |
| P3 | `Alembic`/`Flask-Migrate` sin uso | Quitarlos o adoptarlos |
| P3 | Sin rotación de secretos documentada | Procedimiento + calendario |
| P3 | Logs sin protección anti-manipulación | Backup/exportación de `logs_auditoria` |

## 8. Registro de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Noviembre 2026 | Versión inicial: relevamiento OWASP A08 sobre el estado del repo |
