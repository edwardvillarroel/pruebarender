# Procedimiento de respaldo — PostgreSQL (Supabase)

**Control:** A.8.13 · **Dueño:** administración · **Versión:** 1.0 — 2026-11-06

Cubre la base de datos PostgreSQL de producción alojada en Supabase. **No** cubre los archivos de cotización: desde F4 viven en el bucket privado de Supabase Storage (`Cotizaciones`), fuera de esta base; su retención la aplica el purge (F3) sobre Storage.

## Definiciones (formalizadas)

| Elemento | Definición |
|---|---|
| Periodicidad | **Mensual, el primer lunes de cada mes** + ad-hoc antes de migraciones o cambios grandes |
| Conservación | **6 copias**; al subir la nueva se elimina la que cumpla 6 meses |
| Cifrado | **AES-256 vía 7-Zip** (`.7z` con cabeceras cifradas); contraseña en el gestor de contraseñas — nunca en el servidor, en `public_html` ni en correos |
| Almacenamiento | Carpeta **fuera de `public_html`** en cPanel V2NET (p. ej. `~/backups-apolovibes`), permisos `700` |
| Registro | Obligatorio en `docs/REGISTRO-BACKUPS.md` tras cada ejecución y cada prueba de restauración |

## Requisitos (una sola vez)

1. Cliente PostgreSQL con `pg_dump`: `scoop install postgresql` (o pgAdmin 4, ver paso alternativo).
2. 7-Zip: ya instalado (`7z` en PATH).
3. `DATABASE_URL` (está en el `.env` del repo y en las env vars de Render): apunta al pooler Session de Supabase (`aws-0-sa-east-1.pooler.supabase.com:5432`) — sirve directo para `pg_dump`.
4. Acceso a cPanel V2NET.

## Ejecución mensual (≈10 minutos)

1. **Dump** (desde `C:\Users\jonca\ApoloVibes`):

   ```powershell
   $env:DATABASE_URL = ((Get-Content .\.env) -match '^DATABASE_URL=') -replace '^DATABASE_URL=',''
   $fecha = Get-Date -Format yyyy-MM-dd
   $dump = "$env:USERPROFILE\Downloads\apolovibes_$fecha.dump"
   pg_dump $env:DATABASE_URL --no-owner --no-privileges -Fc -f $dump
   Remove-Item Env:DATABASE_URL
   ```

   Alternativa sin terminal: pgAdmin 4 → clic derecho en la base → *Backup* → formato **Custom** → mismo nombre `apolovibes_aaaa-mm-dd.dump`.

2. **Cifrar** (7-Zip pedirá la contraseña dos veces — no la pongas como argumento):

   ```powershell
$zip = $dump.Replace('.dump','.7z')

7z a -t7z -mhe=on -p $zip $dump
if ($LASTEXITCODE -eq 0) {
    7z t $zip
    if ($LASTEXITCODE -eq 0) { Remove-Item $dump }
    else { Write-Host "El test falló. NO se borró el .dump." }
} else {
    Write-Host "Falló la compresión. NO se borró el .dump."
}
   ```

3. **Subir a cPanel:** *File Manager* → directorio home (**fuera de `public_html`**) → crear/entrar a `backups-apolovibes` → *Upload* del `.7z` → verificar que quedó → *Permissions* de la carpeta: `700`.

4. **Verificar integridad:** descargar el `.7z` desde cPanel a otra carpeta local → abrirlo con la contraseña (o `7z t archivo.7z`) → confirmar tamaño idéntico al original → borrar la copia de prueba.

5. **Eliminar la vencida:** si quedan 7 copias, borrar la más antigua en cPanel y vaciar la papelera.

6. **Registrar** la ejecución en `docs/REGISTRO-BACKUPS.md`.

## Prueba de restauración (primera vez y después al menos anual)

1. Descargar un `.7z` desde cPanel, descifrarlo (obtener el `.dump`).
2. Restaurar en una base de trabajo — opción A, PostgreSQL local:

   ```powershell
   createdb -U postgres apolovibes_restore_test
   pg_restore -U postgres --no-owner -d apolovibes_restore_test .\apolovibes_aaaa-mm-dd.dump
   psql -U postgres -d apolovibes_restore_test -c "select count(*) from solicitudes_diseno;"
   ```

   > **Errores esperados en `pg_restore`:** el volcado incluye objetos propios de Supabase que no existen en una instalación local (`pg_cron`/`cron.*`, políticas sobre los roles `anon`, `authenticated`, `service_role`). En la prueba del 2026-11-06 se reportaron **12 errores ignorados**, todos de esa categoría. **El criterio de éxito son los conteos** (paso 3), no un `pg_restore` sin errores. Nota: `--if-exists` exige `--clean` (`-c`); no usarlo con una BD recién creada y vacía.

   Opción B (prueba de extremo a extremo): crear un proyecto Supabase temporal gratuito, restaurar allí con el mismo `pg_restore`, verificar y **eliminar el proyecto**.

3. **Comparar conteos** con producción (SQL Editor de Supabase): `solicitudes_diseno`, `usuarios`, `pedidos`, `productos`, `pagos` — deben coincidir.
4. Coincidencia → registrar **OK** + fecha en el registro; `dropdb apolovibes_restore_test`.
5. Error o diferencia → tratar como incidente (procedimiento D del SGSI) y regenerar el dump de inmediato.

## Responsabilidades

- Ejecutar, verificar y registrar: **la administración**.
- Nunca dejar un `.dump` sin cifrar en el disco local, en el hosting ni en la nube.
- Este procedimiento es manual e independiente: no hay sincronización automática Supabase ↔ V2NET.
