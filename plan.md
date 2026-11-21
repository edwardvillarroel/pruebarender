PLAN FINAL - Normalización + Bucket público `catalogo` + Optimización Cotizaciones + Fallback Home

*Idea central:*
- La foto nunca se guarda dentro de la tabla. En la tabla solo se guarda la `imagen_url` como texto.
- El archivo `.jpg` real vive en el bucket.
- `Cotizaciones` = privado. `catalogo` = público. Nunca se mezclan.
- Si Supabase se cae, el Home no queda en blanco, muestra vitrina estática desde V2Networks.

---

FASE 1 - Crear bucket público `catalogo`

No toques el bucket `Cotizaciones`. Ese queda privado, con 0 políticas, como está ahora.

1. En Supabase ve a `Storage > New bucket`
2. Nombre: `catalogo`
3. Márcalo como `Public`
-- Lectura pública, cualquiera puede ver las fotos del catálogo
CREATE POLICY "catalogo lectura publica"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'catalogo');

-- Solo tu backend puede subir, nadie desde el front
CREATE POLICY "catalogo solo backend subir"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'catalogo');

-- Solo tu backend puede borrar
CREATE POLICY "catalogo solo backend borrar"
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = 'catalogo');
Resultado:
- `Cotizaciones` = privado
- `catalogo` = público

FASE 2 - Tablas del catálogo

Solo vamos a abrir estas 2 tablas, no las 26.
-- Solo guardamos la URL, no el archivo
ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen_url text;
ALTER TABLE categorias ADD COLUMN IF NOT EXISTS imagen_url text;

-- Para que el front pueda leer los datos del catálogo directo
CREATE POLICY "productos publicos"
ON productos FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "categorias publicas"
ON categorias FOR SELECT
TO anon, authenticated
USING (true);
Ejemplo de cómo queda una fila en `productos`:
nombre	precio	descripcion	imagen_url
Buzo Oversize	34990	Buzo negro...	`https://<tu-proyecto>.supabase.co/storage/v1/object/public/catalogo/productos/buzo.jpg`
FASE 3 - Normalizar `solicitudes_diseno`

Sacar `nombre`, `email`, `telefono` de la tabla de cotizaciones. Esos datos viven en `usuarios`.

*1. Asegura la columna `usuario_id`:*
ALTER TABLE solicitudes_diseno ADD COLUMN IF NOT EXISTS usuario_id uuid;
*2. Rellena `usuario_id` buscando por email:*
UPDATE solicitudes_diseno s
SET usuario_id = u.id
FROM usuarios u
WHERE s.email = u.email
AND s.usuario_id IS NULL;
*3. Revisa las que quedaron sin dueño:*
SELECT COUNT(*) FROM solicitudes_diseno WHERE usuario_id IS NULL;
Si es 0, sigue. Si hay algunas, son cotizaciones de invitados. Se mantienen con `usuario_id` nulo para no perder historial, no se borran.

*4. Crea la FK y borra los duplicados:*
ALTER TABLE solicitudes_diseno
ADD CONSTRAINT fk_solicitudes_usuario
FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
ON DELETE SET NULL;

ALTER TABLE solicitudes_diseno
DROP COLUMN nombre,
DROP COLUMN email,
DROP COLUMN telefono;
Para mostrar el nombre después, usas JOIN:
SELECT s.*, u.nombre, u.email
FROM solicitudes_diseno s
JOIN usuarios u ON u.id = s.usuario_id
WHERE s.id = '...';
Si el usuario se elimina, la cotización no se borra, queda con `usuario_id` nulo pero con historial.

FASE 4 - Backend Render

*A) Admin crea producto - flujo normal, sin cambios para ti:*
Panel Admin -> Backend Render
Tu backend hace 2 cosas:
1. Sube el `.jpg` al bucket `catalogo`, comprimido a menos de 300KB, ideal `.webp` o `.jpg`
   Ejemplo: `catalogo/productos/buzo-oversize-negro-123.jpg`
2. Guarda en `productos`: `nombre, precio, descripcion + imagen_url`

El admin sigue subiendo la foto en el mismo formulario. No sube directo al bucket desde el front, porque eso expondría tu `service_role`.

*B) Cotización - sigue privado:*
Cliente -> Backend Render -> Bucket Cotizaciones (privado)
No cambia a `catalogo`.

*C) Endpoint que crea cotización:*
Ya no guardes `nombre/email/telefono` en `solicitudes_diseno`. Guarda solo `usuario_id`.

*D) Endpoint que lista cotizaciones para el admin:*
Haz el JOIN a `usuarios` para mostrar el nombre.

FASE 4.1 - Optimización Cotizaciones: Thumb + Precarga

Esto es para arreglar que la primera vez que abres el detalle, la imagen demora, y la segunda ya aparece cargada.

*Problema actual:*
Abres lista -> solo texto -> haces click -> recién ahí pide la foto -> espera.

*Solución:*
Abres lista -> en segundo plano ya va bajando las fotitos chicas -> haces click -> la foto ya está en tu navegador.

*1. Al subir la cotización, el backend guarda 2 versiones en el bucket `Cotizaciones` privado:*

- `cotizacion-123.jpg` -> original, para el detalle
- `cotizacion-123-thumb.jpg` -> misma foto pero chica, 400px, menos de 80KB, para la lista

*2. El endpoint de lista devuelve la miniatura:*
{
  "id": "123",
  "cliente": "Jonathan",
  "estado": "pendiente",
  "thumb_url": "https://...url-firmada.../cotizacion-123-thumb.jpg"
}
Esa `thumb_url` es una URL firmada temporal, igual que ahora, pero de la foto chica. Solo se genera después de verificar que el usuario es dueño de esa cotización o es admin. No la generes nueva cada vez, reutilízala por unos minutos.

*3. El front precarga en la lista:*

Cada card de la lista tiene un `<img>` chiquito con esa `thumb_url`, aunque sea de 60px x 60px. El navegador la descarga en segundo plano mientras miras la lista.

Cuando haces click en el detalle, el front muestra al tiro el thumb que ya está en caché, y después cambia a la original cuando termina de bajar. No ves pantalla en blanco.

*Por qué no usar la original en la lista:*
Si tienes 20 cotizaciones de 4MB cada una, abrir la lista bajaría 80MB. Con thumb, 20 x 80KB = 1.6MB.

*Regla:* Cotizaciones sigue privado, siempre con URL firmada. Nunca lo hagas público para que cargue más rápido.

FASE 5 - Frontend

*A) Cliente viendo el catálogo - nuevo flujo, más rápido:*

1. Front lee la tabla `productos` directo: te devuelve `nombre, precio, descripcion, imagen_url` en una sola query
2. El navegador carga la foto directo desde la `imagen_url`: `Front -> Supabase Storage bucket catalogo -> CDN`

O sea:
- *Precio, nombre, descripción:* vienen de la tabla `productos`
- *Foto:* viene del bucket `catalogo`

Con esto desaparece el "...cargando productos por 2 segundos". Ese delay era Render dormido (cold start). Supabase no se duerme, está siempre prendido. Vas a pasar de 2 segundos a 200-400ms la primera vez, y después casi instantáneo por caché.

Importante: si dejas el front llamando a `tu-backend.onrender.com/productos`, vas a seguir viendo los 2 segundos aunque tengas el bucket creado. Hay que cambiar esa llamada a Supabase directo.

*Excepción documentada a la arquitectura:*
Lectura pública del catálogo por CDN directo, excepción al punto de entrada único. Solo `SELECT` con `anon key`, sin datos sensibles, sin escritura. Todo lo mutable sigue por Gateway.

*B) Cotizaciones - sin cambios de arquitectura:*

Siguen por backend. El cliente nunca llama directo a `solicitudes_diseno` ni al bucket `Cotizaciones`. Solo cambia que la lista ya trae el thumb y el detalle muestra el thumb al tiro.

FASE 5.1 - Fallback Home en V2Networks si se cae Supabase

*Problema:*
"Más vendidos de la semana" y "Nuevos lanzamientos" del Home también consultan `productos` en Supabase. Si Supabase se cae, el Home quedaría vacío o con error, igual que el catálogo.

*Solución:*
Dejar una vitrina estática en V2Networks, que es un servicio distinto a Supabase. Si se cae Supabase, V2Networks sigue arriba.

*1. Dejas 6-8 productos fijos en el front:*

En tu proyecto React, en `public/fallback/` dejas:

- `fallback.json` con nombre, precio referencial y descripción de 4 más vendidos + 4 nuevos lanzamientos
- Las fotos de esos 8, comprimidas, en `public/fallback/img/`

Esas fotos viven en V2Networks, no en Supabase. No se caen si se cae Supabase.

*2. El Home intenta lo normal primero:*
Home -> intenta leer Supabase
Si funciona -> muestra los reales, como ahora
Si falla -> muestra el fallback de V2Networks
*3. En modo fallback, con 2 reglas importantes:*

- Se muestra un aviso chico: "Catálogo no disponible en este momento, mostrando selección destacada"
- Se deshabilita el "Agregar al carrito" en esos productos, o se muestra solo como vitrina. Porque el precio de ese `fallback.json` puede estar desactualizado y no quieres vender a un precio viejo.

Así el Home no queda en blanco, el cliente ve que la tienda existe y puede reintentar en unos minutos.

*Qué no hace el fallback:*
No reemplaza al catálogo completo. No son los 100 productos, son solo 8 de vitrina. El catálogo completo sí depende 100% de Supabase, y está bien que así sea.

FASE 6 - Verificación final
-- 1. solicitudes_diseno ya no tiene PII
SELECT column_name FROM information_schema.columns
WHERE table_name = 'solicitudes_diseno'
AND column_name IN ('nombre','email','telefono','usuario_id');
-- Debe salir solo usuario_id

-- 2. Buckets
SELECT id, public FROM storage.buckets;
-- Debe salir: Cotizaciones = false, catalogo = true

-- 3. Políticas de tablas
SELECT tablename, COUNT(*) FROM pg_policies
WHERE schemaname = 'public' GROUP BY tablename;
-- Deben salir solo categorias y productos con 1 cada una

-- 4. Políticas de Storage
SELECT bucket_id, policyname FROM storage.policies;
-- Debe salir catalogo con 3 políticas, Cotizaciones con 0

-- 5. Fallback
-- Apaga Supabase en dev / simula error y verifica que Home muestra fallback.json + aviso + sin botón de compra
---

Resumen en 1 línea

- `Cotizaciones` bucket: privado, no tocar, + thumb + precarga para que el detalle abra al tiro
- `catalogo` bucket: público, nuevo, para categorías / productos
- `productos / categorias`: únicas tablas con política de lectura pública, guardan solo `imagen_url`
- `solicitudes_diseno`: sin `nombre/email/telefono`, solo `usuario_id` + JOIN a `usuarios`, `ON DELETE SET NULL`
- Admin: sube por backend, flujo igual que ahora
- Cliente catálogo: lee datos de tabla + foto directo del bucket, sin Render, sin 2 segundos de carga
- Cliente cotización: lista precarga thumb, detalle muestra thumb al tiro y luego la original
- Home: si Supabase falla, muestra vitrina estática de 8 productos desde V2Networks, sin venta, con aviso