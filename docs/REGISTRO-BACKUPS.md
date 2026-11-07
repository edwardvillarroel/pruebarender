# Registro de respaldos — PostgreSQL (Supabase)

**Control A.8.13 · Instrucciones: `docs/PROCEDIMIENTO-BACKUP-SUPABASE.md`**

Completar una fila después de **cada ejecución** y de **cada prueba de restauración**. Las filas no se editan después: si hay un error, se agrega una fila nueva que lo documente.

| # | Fecha dump | Archivo | Tamaño | Verificación (descarga + prueba de contraseña) | Restauración de prueba (fecha y resultado) | Copia eliminada | Responsable |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-06 | apolovibes_2026-11-06.7z | 16.507.347 B (dump plano 16.922.823 B) | **OK** — descarga desde cPanel + `7z t` con contraseña: Everything OK (2026-11-06) | 2026-11-06 — **OK**: restauración local en PostgreSQL 18.6 previa al cifrado; conteos idénticos a producción (solicitudes_diseno 21, usuarios 16, pedidos 26, productos 35, pagos 26); 12 errores ignorados por objetos Supabase (esperados) | — | administración |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| 5 | | | | | | | |
| 6 | | | | | | | |
| 7 | | | | | | | |

**Retención:** conservar 6 copias. Al registrar la copia #7, eliminar en cPanel la más antigua y anotarla en la columna «Copia eliminada».
