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

> **Nota de desviación (2026-09-13):** la entidad `Producto` agregó dos
> columnas a `productos` para almacenar la imagen como BLOB dentro de la BD:
> `imagen_bytes` (BLOB) y `imagen_content_type` (VARCHAR2(50)). La columna
> `imagen` sigue existiendo pero ahora apunta a la URL del endpoint
> `GET /api/productos/<id>/imagen` que sirve esos bytes. La migración se hace
> manualmente (`migrar_imagen_blob.py`) y el alta vía `agregar_producto.py`,
> ambos fuera de git.

> **Nota de desviación (2026-09-26):** un producto puede tener N variantes de
> color, cada una con su propia foto. Esto agrega la tabla `producto_colores`
> (entidad `ColorProducto` en `domain/entities/producto.py`, modelo
> `ProductoColorModel`), más la columna `color` en `carrito_items` y en
> `detalle_pedidos`. `productos.imagen_bytes` queda como imagen principal y
> fallback para los productos sin variantes. En el carrito, dos líneas del
> mismo producto solo se fusionan si comparten producto **y** color, porque se
> imprimen distinto. La restricción única `UQ_CARRITO_ITEM_PRODUCTO`
> (carrito_id, producto_id) de la tabla original fue reemplazada por
> `ux_carrito_item_producto_color` sobre
> `(carrito_id, producto_id, NVL(color, ' '))`; el `NVL` es necesario porque en
> Oracle NULL no es igual a NULL dentro de un índice único. Migración:
> `migrations/crear_producto_colores.sql`.
>
> `GET /api/productos` completa la foto de los productos que no tienen
> `imagen_bytes` con la del **primer** color (`primera_imagen_color_por_producto`,
> una sola consulta con `min(orden) GROUP BY`, no una por producto). Así la
> tarjeta del catálogo no queda vacía para productos creados solo con
> variantes. `GET /api/productos/:id` sí devuelve la foto principal tal cual.

> **Nota de desviación (2026-09-26):** el catálogo servía fotos de 3-4 MB en
> tarjetas de ~240px: 19 productos con foto son 100,69 MB de BLOB y 2,4 MB en
> promedio por visita. Se agregan cuatro columnas —`imagen_thumb_bytes` (BLOB) y
> `imagen_thumb_content_type` (VARCHAR2(50)) en `productos`, y las mismas dos en
> `producto_colores`— que guardan una versión reducida: lado mayor de 600px,
> JPEG quality 82. La **original queda intacta**: el detalle del producto y el
> selector de color necesitan resolución completa, y `/imagen` sigue sirviendo
> el archivo entero. Migración: `migrations/agregar_thumbnails.sql`.
>
> Las cuatro columnas están declaradas `deferred` en los modelos ORM. El listado
> del catálogo pregunta solo por su existencia
> (`imagen_thumb_bytes.isnot(None)`) en el mismo `SELECT` del modelo: leer el
> atributo dentro del mapeo dispararía una consulta extra por producto (N+1) y el
> listado volvería a ir lento, que es justo lo que se vino a arreglar.
>
> La generación es **perezosa**: no hay paso de backfill obligatorio. Si el
> thumbnail no existe cuando se pide, `GET /api/productos/:id/thumb` (o
> `.../colores/:id/thumb`) lo genera desde el original, lo guarda y lo sirve; las
> peticiones siguientes ya leen el BLOB. Si no se puede generar —la foto ya es
> chica, es ilegible, o falta Pillow— la ruta sirve la original en vez de dejar
> la tarjeta rota. Cuando se reemplaza la foto, el thumbnail se invalida en el
> mismo `UPDATE` que la original: es un invariante de persistencia, no una
> operación aparte del caso de uso.
>
> El JSON de `GET /api/productos` y el de colores ya incluyen el campo
> `imagen_thumb` con la URL del thumbnail, o `null` cuando todavía no existe (y
> también cuando la foto no necesita reducción). El frontend usa el patrón
> `imagen_thumb || imagen` en la grilla (`ProductCard.jsx`) y en los swatches de
> color (`ProductoDetalle.jsx`), de modo que cae a la original mientras el
> thumbnail no exista. El script `generar_thumbnails.py` (raíz, fuera de git)
> permite adelantarlo si se quiere, con `--what-if` para ensayo.

> **Nota de desviación (2026-09-28):** `productos` gana la columna
> `nuevo_lanzamiento` (`NUMBER(1) DEFAULT 0 NOT NULL`), un flag que el admin
> prende desde el modal de producto y que decide si el producto sale en la
> sección **«Lanzamientos»** de la home. No es lo mismo que `activo`, que es el
> borrado lógico: un producto puede estar activo y no ser un lanzamiento.
> Migración: `migrations/agregar_nuevo_lanzamiento.sql`.
>
> El flag es un booleano y **no** se deriva de la fecha ni de la etiqueta. La
> home ordena los lanzamientos del más nuevo al más viejo, así que el JSON de
> `GET /api/productos` ahora incluye `creado_en` (ISO 8601) además de
> `nuevo_lanzamiento`: sin la fecha en la respuesta la sección no se puede
> ordenar, porque la API ordena por `nombre`.
>
> La etiqueta que ve la tarjeta (`badge`) se **deriva en `_a_publico_producto`**
> y no se persiste nunca. La columna `productos.badge` queda reservada para
> valores manuales (hay productos con «Best Seller») y así conviven «Nuevo» y
> «Best Seller» sin pisarse. Derivarla y guardarla en la misma columna es un
> error: el repositorio volvería a leer su propio valor derivado, y apagar el
> flag dejaría el «Nuevo» pegado en la fila para siempre.
>
> `PATCH /api/productos/:id` distingue tres estados con `is not None`: ausente
> = no tocar, `true` = marcar, `false` = desmarcar. Por eso el modal manda el
> campo siempre, incluso en `false`: con un chequeo truthy el `false` nunca se
> aplicaría y un lanzamiento no se podría apagar.

> **Nota de desviación (2026-10-21):** «Los más vendidos» es un **ranking
> calculado**, no una etiqueta manual. La columna `productos.badge` sigue
> reservada para valores manuales (hay productos con «Best Seller» escritos a
> mano), pero la home y el panel de admin piden el ranking real a
> `GET /api/productos/mas-vendidos`.
>
> La regla de qué es «vendido» es una sola: **pago `completado`**. Es el mismo
> criterio con el que se descuenta el stock, así que el ranking no puede
> contar pedidos que nunca se pagaron (carrito abandonado, pasarela que
> devuelve `failed`, pestaña cerrada). El filtro va en el repositorio, no en el
> frontend, que es el que hay que cambiar cada vez que aparece una pantalla
> nueva.
>
> El filtro de pago se escribe con `EXISTS` y **no** con `JOIN` a `pagos`: un
> pedido puede tener varias filas en `pagos` (el reintento típico de pasarela
> deja un `fallido` y después un `completado`) y un `JOIN` multiplicaría las
> líneas de `detalle_pedidos`, inflando el `SUM` de unidades. Con `EXISTS` cada
> línea cuenta una vez, sin importar cuántos intentos de pago tenga el pedido.
>
> La ventana de venta (`periodo`) se aplica sobre `pagos.creado_en` —cuando se
> cobró—, no sobre `pedidos.creado_en` —cuando se pidió—. Lo que interesa es
> cuándo se vendió, no cuándo se escribió el pedido.
>
> `ingresos` es la suma de `cantidad × precio_unitario`, con el precio
> **histórico** del `detalle_pedidos`: es lo que entró de verdad, y no tiene por
> qué coincidir con el precio actual del catálogo si el producto cambió de
> precio después de la compra.

> **Nota de desviación (2026-10-22):** facturación electrónica (DTE) vía
> OpenFactura (Haulmer). El backend emite **boleta electrónica (DTE 39)** o
> **factura electrónica (DTE 33)** una vez que el pago queda `completado`.
> Proveedor: `POST https://api.haulmer.com/v2/dte/document` (dev:
> `dev-api.haulmer.com`, con CAF simulado), cabeceras `apikey` e
> `Idempotency-Key`.
>
> **Los datos del receptor ya estaban capturados.** El checkout guarda en
> `pedidos.direccion_envio` el JSON del cliente (`tipoDocumento`, `rut`,
> `razonSocial`, `giro`, dirección, comuna). No se agregó una columna con los
> datos fiscales: se usa ese JSON. Lo único nuevo en `pedidos` es
> `tipo_documento` (`boleta` | `factura`), que permite consultar de una
> vez cuáles pedidos esperan factura. La tabla nueva `documentos_tributarios` guarda
> lo emitido: folio, token, montos, estado y el PDF en `bytea`.
>
> **Los dos formatos no son el mismo payload.** El proveedor los valida con su
> propio XSD y los rechaza si les sobra o les falta un campo:
>
> | | Boleta (39) | Factura (33) |
> |---|---|---|
> | Líneas | precio **bruto** (IVA incluido) | precio **neto** |
> | Totales | `MntNeto`, `IVA`, `MntTotal`, `VlrPagar` | + `TasaIVA` (`19`) |
> | Medio de pago | `MedioPago` | `FmaPago` |
> | Emisor | `CdgSIISucur` | `Acteco` |
> | Receptor | basta el RUT | razón social, giro, dirección y comuna obligatorios |
>
> **El IVA va por diferencia.** El precio del catálogo es bruto y el total
> cobrado es un entero de pesos, pero `total / 1.19` casi nunca da un entero.
> La regla implementada (`app/domain/facturacion.py`) es
> `neto = redondeo(total / 1.19)` e `IVA = total - neto`: el IVA canónico del
> 19% puede quedar un peso arriba o abajo, que es justo lo que el proveedor
> acepta (tolerancia ±1 verificada contra la API), y a cambio **el total del
> comprobante es exactamente lo que se cobró**. El desglose vive en `domain`
> porque lo usan el cliente del proveedor (`infrastructure`) y el caso de uso
> de emisión (`application`), y los módulos de `application` no se importan
> entre sí.
>
> **La emisión es idempotente y de dos pasos.** La clave es
> `dte-<pedido_id>`: sale del pedido, así que es siempre la misma. El
> proveedor la respeta de verdad: repetirla responde `OF-06` con el token del
> documento ya emitido, y con ese token se recupera el PDF
> (`GET /v2/dte/document/{token}/pdf`). Por eso el caso de uso
> (`app/application/facturacion/emitir_documento_tributario.py`) reserva la
> fila antes de llamar al proveedor y, si recibe `OF-06`, **recupera** el
> documento en vez de darlo por fallido. Un `UNIQUE` sobre `pedido_id` y otro
> sobre `clave_idempotencia` cierran la puerta por el lado de la base.
>
> **Fallar la facturación NO puede fallar el pago.** La emisión es
> best-effort: `ProcesarPago` la llama después de confirmar el pago, captura
> la excepción y sigue. El error queda en la fila del documento (`estado =
> 'error'`) y se reintenta en la próxima confirmación (la pasarela reintenta
> el callback hasta 10 veces). Un documento con `estado = 'error'` se vuelve a
> pedir: la idempotencia del proveedor lo impide duplicar.
>
> **Sin configuración no hay documento, pero el pago sigue.** Si falta
> `OPENFACTURA_API_KEY` o `EMISOR_RUT`, `app/__init__.py` no inyecta el
> servicio de documentación y el sistema funciona igual, solo que sin
> comprobante electrónico. `tools/verificar_openfactura.py` es el script de
> Fase 0: verifica key, folios disponibles y datos del emisor, y con
> `--emitir` emite un documento de prueba.
>
> **Lo que no se emite:** si el receptor es un pasaporte (no un RUT), no hay
> documento: la API de boleta solo acepta `RUTRecep`. Se prefirió no emitir
> antes que emitir un comprobante a nombre equivocado.

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
GET    /api/productos                  # catálogo público
                                       #   + nuevo_lanzamiento (bool), creado_en (ISO)
                                       #   + badge: "Nuevo" si nuevo_lanzamiento,
                                       #     si no el badge manual de la fila
GET    /api/productos/mas-vendidos     # ranking público por unidades vendidas
                                       #   ?periodo=7d|30d|todo (default "todo")
                                       #   &limite=1..50 (default 10)
                                       #   → { productos: [ { ...producto,
                                       #                      unidades_vendidas,
                                       #                      ingresos } ],
                                       #       periodo, total }
                                       #   cuenta solo pagos "completado";
                                       #   periodo inválido → 400 { mensaje }
GET    /api/productos/:id              # detalle público (mismos campos)
GET    /api/productos/:id/imagen       # imagen en BLOB (content-type real)
GET    /api/productos/:id/thumb        # thumbnail del producto (600px, JPEG q82)
GET    /api/productos/:id/colores      # variantes de color del producto
GET    /api/productos/colores/:id/imagen  # imagen de una variante de color
GET    /api/productos/colores/:id/thumb   # thumbnail de una variante de color
POST   /api/productos/:id/colores      # crea/reemplaza color + foto (multipart: color, imagen)
DELETE /api/productos/colores/:id      # elimina una variante de color
GET    /api/categorias

POST   /api/pedidos
GET    /api/pedidos/:id
GET    /api/pedidos/:id/documento        # comprobante electrónico del pedido
                                        #   → { folio, estado, tipo, montos, ... }
                                        #   404 si el pedido no tiene documento
GET    /api/pedidos/:id/documento/pdf    # PDF del comprobante (application/pdf)

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
│   │   ├── facturacion.py
│   │   ├── time.py
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
│   │   │   ├── notificacion.py
│   │   │   └── documento_tributario.py
│   │   └── interfaces/
│   │       ├── __init__.py
│   │       ├── repository_base.py
│   │       ├── uow.py
│   │       ├── facturacion.py
│   │       └── repositories.py
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── common/
│   │   │   ├── __init__.py
│   │   │   ├── dto.py
│   │   │   └── facturacion.py
│   │   ├── facturacion/
│   │   │   ├── __init__.py
│   │   │   ├── emitir_documento_tributario.py
│   │   │   └── consultar_documento_tributario.py
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
│   │   │       ├── notificacion_model.py
│   │   │       └── documento_tributario_model.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── repository_base.py
│   │   │   ├── usuario_repository.py
│   │   │   ├── producto_repository.py
│   │   │   ├── pedido_repository.py
│   │   │   ├── pago_repository.py
│   │   │   ├── solicitud_diseno_repository.py
│   │   │   ├── notificacion_repository.py
│   │   │   └── documento_tributario_repository.py
│   │   ├── facturacion/
│   │   │   ├── __init__.py
│   │   │   └── openfactura_cliente.py
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
- [ ] Facturacion electronica en produccion: API key propia de la organizacion
      `78.064.166-5`, CAF vigente (el de dev es simulado), `EMISOR_*` con los
      datos reales que entrega `GET /v2/dte/taxpayer/{rut}`, y `OPENFACTURA_API_URL`
      apuntando a `https://api.haulmer.com`
- [ ] Mostrar el comprobante en la UI (`MisPedidos`): folio, tipo de documento y
      descarga del PDF contra `GET /api/pedidos/:id/documento{,/pdf}`
