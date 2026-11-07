# SGSI Interno — ApoloVibes 3D

**Clasificación: CONFIDENCIAL**

Basado en ISO/IEC 27001:2022 — Versión 1.2 — Vigente desde noviembre de 2026 · Próxima revisión: mayo de 2027

---

## Naturaleza y uso del documento

El presente documento consolida el estado conocido de los activos tecnológicos, los principales riesgos de seguridad, los controles identificados y las brechas que requieren implementación o verificaciones. Las referencias a rutas de código, configuraciones y proveedores se incluyen para facilitar el seguimiento técnico por parte de la administración autorizada.

Las medidas descritas como pendientes no deben interpretarse como controles ya implementados. Cuando una condición depende de un panel externo o de una revisión técnica no realizada, se identifica expresamente como verificación pendiente.

## A. Activos identificados

- Dominio https://apolovibes3d.cl (estático en V2NET + cPanel V2N).
- API y backend Flask en Render (api.apolovibes3d.cl).
- Servicio de cotización IA en Render (https://cotizadorapoloai.onrender.com, puerto 8001, repo externo: verificar stack y modelos, y confirmar que las imágenes no se envían a ninguna API externa).
- Base de datos PostgreSQL en Supabase (plan gratis).
- Cuenta Resend (correo transaccional).
- Pasarela de pagos Tuu.
- Google OAuth (inicio de sesión con Google) y Google reCAPTCHA (registro e inicio de sesión).
- Archivos de cotización en `uploads/cotizaciones/` (Render, disco efímero).
- Datos de despacho (nombre, dirección, contacto) compartidos con Starken y Bluexpress.
- Datos de facturación del checkout (RUT, razón social y giro, si hay factura).
- Impresoras.

## B. Evaluación de Riesgos (Top 5)

1. **Filtración de imágenes/cotizaciones de clientes — Impacto Alto.**
   Mitigación vigente (2026-11-06): nombres UUID, validación de contenido y **URLs firmadas**. `GET /api/uploads/<path>` exige una firma HMAC-SHA256 con expiración de 24 horas (`?exp=&sig=`); sin firma válida responde 403 (`app/api/routes/diseno_routes.py`, `app/infrastructure/imagenes/firmas_upload.py`). Quien posea una URL firmada puede ver la imagen hasta que expire; las firmas se emiten al consultar las cotizaciones (sesión requerida en esos endpoints).

2. **Acceso no autorizado a cPanel V2N — Impacto Alto.**
   Mitigación declarada: 2FA activo, contraseña de 16 caracteres, IP whitelist.
   Verificar en el panel de V2NET (no verificable desde el repo).

3. **Inyección de archivo malicioso en el cotizador — Impacto Medio.**
   Mitigación: validación real por magic bytes + patrones sospechosos + verificación PIL (`app/infrastructure/imagenes/validador_imagen_segura.py`), límite de 8 MB en frontend (`Cotizacion.jsx:131`) / 10 MB en backend (`app/config.py:117`).
   Nota: `ai_edge_litert` no está en este repo — verificar stack y modelos en el repo del cotizador (https://cotizadorapoloai.onrender.com, puerto 8001).

4. **Pérdida de archivos por disco efímero — Impacto Medio.**
   Mitigación vigente (2026-11-06): purge automático semanal de filas y archivos de cotización (ver A.8.10 y F3) — la retención publicada de 12 meses para cotizaciones no concretadas quedó respaldada por infraestructura.
   Estado F4 (2026-11-06): código implementado para persistir los archivos en el bucket privado de Supabase Storage (`Cotizaciones`) con redirección 302 a URL firmada y endpoint de migración. **Pendiente de despliegue y de ejecutar la migración en Render** — hasta entonces los archivos siguen en el disco efímero y se pierden en cada redeploy (ver pendiente F4).

5. **Pérdida de la base de datos por ausencia de respaldos — Impacto Alto.**
   Mitigación definida: procedimiento de respaldo manual de la base de datos PostgreSQL alojada en Supabase.
   La administración descargará periódicamente una exportación de la base de datos (db dump) desde Supabase y almacenará una copia fuera de ese servicio.
   El almacenamiento externo definido será un espacio privado del hosting V2NET mediante cPanel, fuera del directorio público public_html, con acceso restringido y protección mediante cifrado.
   La administración será responsable de verificar los respaldos, controlar su conservación y eliminar las copias que superen el período de retención definido.
   Este procedimiento no contempla conexiones automáticas entre Supabase y V2NET ni tareas programadas.
   Los respaldos de PostgreSQL no incluyen automáticamente los archivos almacenados en servicios de almacenamiento de objetos; estos requieren un procedimiento independiente.
   Ver A.8.13 y pendientes F.

## C. Controles Anexo A aplicados

- **A.5.15 Control de acceso:** roles en BD limitados a `admin` y `cliente` (CHECK en `migrations/postgres/schema_completo.sql:84` y `usuarios.sql:18`). El panel admin requiere sesión JWT + MFA/TOTP: las primitivas de hash y TOTP están en `gateway/domain/seguridad.py`, y el bloqueo tras 3 fallos en `gateway/application/auth.py` (`UMBRAL_FALLOS_MFA = 3`). No existe rol "DUEÑO" ni campo `costo_filamento`.
- **A.8.10 Eliminación:** implementado parcialmente (2026-11-06). Purge automático semanal (GitHub Actions → `POST /api/admin/cotizaciones/purgar`, protegido con `CRON_SECRET`): elimina filas de cotización de más de 12 meses sin pedido asociado, sus archivos y los archivos huérfanos de `uploads/cotizaciones/`. Además, `DELETE /api/cotizaciones/<id>` (solo admin) borra la fila y el archivo de una cotización concreta. Script de respaldo manual: `scripts/purgar_cotizaciones.py`. Ruta real de archivos: `uploads/cotizaciones/` (`app/config.py:119`, `app/infrastructure/imagenes/almacen_cotizaciones.py:6`).
  Procedimiento manual para solicitudes de eliminación de titulares (compromiso público: 48 horas): (1) verificar la identidad del titular por el correo con el que cotizó; (2) borrar sus cotizaciones con `DELETE /api/cotizaciones/<id>` (borra fila y archivo) y sus datos asociados en Supabase; (3) borrar cualquier exportación manual de la base que contenga sus datos; (4) responder al titular y dejar registro en bitácora. Quedan fuera los datos que deban conservarse por obligaciones legales o tributarias (ver F6).
- **A.8.24 Cifrado:** TLS en web, API y Resend. Verificación pendiente en los paneles de Render y Supabase (no verificable desde el repo).
- **A.8.13 Backup:** Supabase aloja la base de datos PostgreSQL de producción. Se establece un procedimiento de respaldo manual mediante exportaciones (db dump) descargadas desde Supabase y almacenadas en un espacio privado de cPanel V2NET, fuera de public_html.
  El almacenamiento deberá contar con acceso restringido y protección mediante cifrado. La administración será responsable de verificar los archivos, controlar su período de conservación y eliminar las copias vencidas.
  No existe integración automática ni sincronización programada entre Supabase y V2NET. Periodicidad: mensual (primer lunes). Conservación: 6 copias. Cifrado: AES-256 (7-Zip) con contraseña en el gestor de contraseñas. Registro de ejecuciones y pruebas de restauración en `docs/REGISTRO-BACKUPS.md`; procedimiento completo en `docs/PROCEDIMIENTO-BACKUP-SUPABASE.md`.
  Este control cubre la base de datos PostgreSQL, no los archivos de cotización almacenados en otros servicios (ver F4).
- **A.5.33 Protección de datos:** el cotizador no solicita RUT como dato necesario para analizar las imágenes. El checkout recopila datos de identificación, contacto y despacho; cuando el cliente solicita factura, también RUT, razón social y giro. Los datos de checkout y los plazos de conservación están descritos en la política pública v1.2. Los datos necesarios para el despacho se comparten con Starken y Bluexpress; las imágenes de referencia de los clientes no se comparten con las empresas de transporte.

## D. Procedimiento de Incidentes

Si hay fuga:

1. Desconectar la API.
2. Evaluar el alcance: qué datos y qué clientes están afectados.
3. Avisar a los clientes afectados lo antes posible (objetivo interno: menos de 72 horas).
4. Evaluar si corresponde notificar a la Agencia de Protección de Datos Personales y a los titulares afectados.
5. Registro en bitácora.

Nota: la Ley N° 21.719 (art. 14 sexies) exige notificar a la Agencia por los medios más expeditos posibles y **sin dilaciones indebidas**; no fija un plazo de 72 horas. Las 72 horas son un objetivo interno de referencia, no el estándar legal. Verificar las obligaciones y plazos de notificación de la Ley 21.719 antes de dar el procedimiento por consistente con ella.

## E. Revisión

Cada 6 meses, y cada vez que cambie la infraestructura o un proveedor. Próxima revisión: mayo de 2027.

## F. Pendientes de implementación

1. ~~(Prioridad alta) Restringir `GET /api/uploads/<path>` con sesión (`diseno_routes.py`)~~ — **Resuelto (2026-11-06):** URLs firmadas HMAC-SHA256 con expiración de 24 h (`?exp=&sig=`) exigidas en `servir_uploads` (F1).
2. (Prioridad alta) Respaldos — **resuelto (2026-11-06):** exportación mensual manual desde Supabase (`pg_dump`), cifrado AES-256 (7-Zip), carpeta privada en cPanel V2NET fuera de `public_html`, conservación de 6 copias y registro obligatorio en `docs/REGISTRO-BACKUPS.md` — detalle en `docs/PROCEDIMIENTO-BACKUP-SUPABASE.md`. **Primera ejecución completada (fila 1 del registro):** dump 2026-11-06, verificación de descarga y contraseña OK, primera prueba de restauración OK (conteos coinciden con producción). Próxima ejecución: primer lunes de diciembre. No cubre los archivos de cotización (ver F4).
3. ~~Purge automático de archivos y filas de cotización según el plazo publicado en la política (12 meses para cotizaciones no concretadas) — hoy no existe ningún mecanismo. Mientras no exista, no ampliar la promesa pública.~~ — **Resuelto (2026-11-06):** purge semanal vía GitHub Actions (`POST /api/admin/cotizaciones/purgar`: filas de 12 meses sin pedido + huérfanos de `uploads/cotizaciones/`) y DELETE admin manual (48 h, A.8.10) (F3).
4. ~~Persistencia de los archivos de cotización fuera del disco efímero de Render (p. ej. Supabase Storage u objeto S3) para que la retención publicada y los respaldos sean confiables.~~ — **Implementado (2026-11-06), pendiente de despliegue:** archivos en bucket privado de Supabase Storage (`Cotizaciones`, service-role solo en servidor), `servir_uploads` verifica la firma F1 y redirige (302) a URL firmada corta, purge (F3) borra del bucket, y `POST /api/admin/cotizaciones/migrar` (mismo guard `X-Cron-Secret`, con `dry_run`) sube los archivos del disco de Render. **Pendiente:** (1) env vars `SUPABASE_*` en Render, (2) commit + despliegue, (3) ejecutar la migración en Render **antes del próximo redeploy**, (4) verificar una cotización real end-to-end. Hasta ejecutar la migración, los archivos siguen en el disco efímero.
5. Revisar el repositorio completo y las dependencias del cotizador IA (https://cotizadorapoloai.onrender.com) para confirmar que el procesamiento de imágenes se realiza dentro del servicio de Render y que no existen llamadas a APIs externas de inteligencia artificial. El código fuente proporcionado utiliza modelos TensorFlow Lite locales (`ai-edge-litert`) y no muestra llamadas a servicios externos de IA; si la revisión completa identifica alguna integración externa, actualizar la Política de Privacidad Pública.
6. Definir qué datos deben conservarse por obligaciones legales o tributarias y confirmar los plazos con el contador (la política pública ya declara 6 años para boletas y facturas) y agregar esa excepción a la promesa de eliminación.
7. Revisar los términos de tratamiento de datos de V2NET, Render, Supabase, Resend, Tuu, Google, Starken y Bluexpress.
8. ~~Buzones contacto@ / seguridad@ (hoy se usa apolovibes3d@gmail.com).~~ — **Resuelto (2026-11-06):** buzones `contacto@apolovibes3d.cl` y `seguridad@apolovibes3d.cl` creados en cPanel V2NET con reenvío a apolovibes3d@gmail.com (MX del dominio ya apuntaba al hosting).
9. Medición de disponibilidad.

---

| Versión | Fecha | Descripción |
|---|---|---|
| 1.1 | Noviembre 2026 | Versión inicial de la política. |
| 1.2 | Noviembre 2026 | Actualización y formalización de las disposiciones internas de seguridad de la información. |
