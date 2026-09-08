# Forma3D — Frontend (React)

Estructura base de la tienda de impresión 3D en React + Vite + React Router.

## Instalación

```bash
npm install
npm run dev
```

## Estructura

```
src/
  components/       Navbar, Footer, HeroVideo, ProductCard
  pages/            Home, Categorias, ProductoDetalle, Carrito,
                     Checkout, PagoRetorno, Cotizacion
  pages/admin/       AdminLayout, Dashboard, Pedidos, Productos,
                     Inventario, Cotizaciones
  context/          CartContext (estado global del carrito)
  services/         api.js (cliente HTTP), payment.js (Webpay)
  data/             products.js (datos mock, mientras no hay backend)
  styles/           global.css (tokens de diseño: color, tipografía)
```

## Rutas

| Ruta | Página |
|---|---|
| `/` | Home con video hero |
| `/categorias` | Catálogo filtrable |
| `/producto/:id` | Detalle de producto |
| `/carrito` | Carrito de compras |
| `/checkout` | Datos de envío + pago |
| `/pago/retorno` | Confirmación tras Webpay |
| `/cotizar` | Formulario de cotización con imagen |
| `/admin` | Dashboard |
| `/admin/pedidos` | Pedidos |
| `/admin/productos` | Productos |
| `/admin/inventario` | Inventario |
| `/admin/cotizaciones` | Revisión de cotizaciones |

## Lo que falta conectar (backend)

Este frontend está listo para conectarse a una API REST. Ninguna de estas
piezas puede vivir solo en el navegador por seguridad:

1. **Pago (Webpay Plus / Transbank)**
   - `POST /api/pago/crear` → crea la transacción con la llave de comercio
     (guardada en el servidor) y devuelve `{ url, token }`.
   - `POST /api/pago/confirmar` → confirma el resultado con Transbank.
   - Si prefieres otra pasarela (Flow, MercadoPago, Khipu) solo se
     reemplaza `src/services/payment.js`; el resto de la app no cambia.

2. **Cotización con imagen**
   - `POST /api/cotizaciones` (multipart/form-data) → guarda la imagen
     (ej. en S3 o disco), crea el registro y **envía un correo/WhatsApp
     al dueño** con los datos y el link a la imagen.
   - `GET /api/cotizaciones` → lista para el panel admin.
   - `PATCH /api/cotizaciones/:id` → aprobar (con precio) o rechazar;
     debería disparar un correo automático de vuelta al cliente.

3. **Autenticación del panel admin**
   - `/admin/*` hoy es una ruta pública. Antes de producción, protegerla
     con login + rutas privadas (JWT o sesión) para que solo el dueño
     y su equipo puedan entrar.

4. **Video del Home**
   - Colocar los archivos en `public/media/`:
     `hero-print-timelapse.mp4`, `hero-print-timelapse.webm` y
     `hero-poster.jpg` (imagen de respaldo mientras carga).
