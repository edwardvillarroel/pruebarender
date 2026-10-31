import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { mediaPath } from '../utils/media.js'
import { fechaLegalLarga } from '../services/legal.js'
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js'

const CONTENT = {
  terminos: {
    titulo: 'Términos y Condiciones',
    actualizacion: fechaLegalLarga(),
    texto:
      `1. Identificación del Proveedor
El sitio de Apolo Vibes 3D es operado por Apolo Vibes SPA, RUT: 78.064.166-5 con domicilio en calle Pasaje el Boldo Nro:33, Viña del Mar, Chile. Puede contactarnos en apolovibes3d@gmail.com.

2. Aceptación de los Términos
Al acceder y utilizar el Sitio, usted acepta estos Términos y Condiciones. Si no está de acuerdo con ellos, le solicitamos no utilizar el Sitio.

3. Descripción del Servicio
Apolo Vibes 3D es una tienda en línea de figuras de colección y artículos impresos en 3D, accesorios, llaveros y diseños personalizados. Podemos modificar o discontinuar aspectos del servicio, sin que ello afecte los pedidos ya confirmados.

4. Productos y Precios
Los productos están sujetos a disponibilidad. Los precios se expresan en pesos chilenos (CLP) e incluyen IVA. El precio que se respeta es el vigente al momento de confirmar su pedido; los cambios de precio solo afectan compras futuras. Las imágenes son referenciales y pueden diferir ligeramente del producto final. Emitimos boleta o factura según el documento que seleccione al confirmar su pedido.

5. Pedidos, Confirmación y Cotizaciones
Los pedidos están sujetos a confirmación de stock. Si un producto pagado no estuviera disponible, se lo informaremos y le devolveremos el dinero por el mismo medio de pago. Cuando su pago se confirme, le enviaremos por correo el comprobante con el detalle del pedido. Si no lo recibe, puede solicitarlo a apolovibes3d@gmail.com.
Las cotizaciones generadas con nuestro cotizador automatizado son estimaciones y pueden variar según la complejidad del diseño, los materiales y las condiciones de fabricación. El precio definitivo será confirmado por nuestro equipo antes de producir.

6. Formas de Pago
Aceptamos los medios de pago disponibles en el checkout, incluyendo tarjetas de crédito y débito a través de la plataforma Tuu. El procesamiento de pagos está sujeto a las políticas de ese proveedor. Apolo Vibes 3D no almacena los datos de su tarjeta.

7. Envíos y Entregas
Puede elegir envío a domicilio o retiro en Álvarez 1106, Viña del Mar, según las opciones disponibles durante la compra. Los plazos de entrega se informan en el checkout y pueden variar según la ubicación y la complejidad de los pedidos personalizados. Trabajamos con empresas de transporte externas, como Starken, pero somos responsables frente a usted por la entrega de su pedido. Si hay retrasos, se lo comunicaremos y podrá ejercer los derechos que le reconoce la ley.

8. Derecho de Retracto
De acuerdo con la Ley 19.496, en las compras realizadas a través del Sitio usted puede arrepentirse dentro de 10 días contados desde la recepción del producto, sin necesidad de expresar causa.
Para ejercerlo, escríbanos a apolovibes3d@gmail.com indicando su número de pedido. El producto debe devolverse sin uso, completo y con su embalaje original. Le reembolsaremos el precio pagado por el mismo medio de pago, dentro del plazo legal. Los costos de devolución serán de cargo del cliente.
El retracto no aplica a productos confeccionados según las especificaciones del cliente o claramente personalizados (por ejemplo, diseños a medida), ni a los demás casos de exclusión que establece la ley.
Ejercer o no el retracto no afecta su derecho a la garantía legal.

9. Garantía Legal
Si un producto presenta fallas o defectos, o no es apto para su uso, usted tiene derecho a la garantía legal de 6 meses desde la recepción del producto (para productos nuevos). Puede elegir la reposición del producto o la devolución de lo pagado, en los términos de los artículos 19 a 21 de la Ley 19.496.
Para solicitarla, escríbanos a apolovibes3d@gmail.com con su número de pedido y, si es posible, fotografías del problema. No se aplica cuando el defecto se debe a mal uso, manipulación indebida o desgaste normal.

10. Pedidos Personalizados y Cancelación
Los diseños a medida son orientativos: el producto final puede diferir de la visualización o referencia aprobada. La fabricación comienza una vez aprobado el diseño definitivo y confirmado el pago.
Puede cancelar un pedido personalizado sin costo antes de que comience la producción. Una vez iniciada, podremos cobrar los costos de materiales y trabajo ya incurridos. Si el producto llega con fallas, aplica la garantía legal.

11. Contenido y Diseños Aportados por el Cliente
Si usted nos envía imágenes, modelos o ideas para un pedido personalizado, declara ser su titular o contar con las autorizaciones necesarias. Nos reservamos el derecho de rechazar pedidos que infrinjan derechos de autor, marcas u otros derechos de terceros. Usted nos autoriza a usar ese contenido solo para cotizar y fabricar su pedido.

12. Propiedad Intelectual
Los textos, gráficos, logotipos, imágenes, modelos 3D y software del Sitio son propiedad de Apolo Vibes 3D o de sus proveedores y están protegidos por la legislación chilena e internacional.

13. Responsabilidad
Apolo Vibes 3D responde en los términos que establece la ley. Nada en estos Términos limita o excluye los derechos irrenunciables que la Ley 19.496 reconoce a los consumidores.

14. Reclamos y Solución de Controversias
Si tiene un problema, escríbanos primero a apolovibes3d@gmail.com y buscaremos una solución. También puede acudir al SERNAC o al Juzgado de Policía Local competente, conforme a la Ley 19.496.

15. Legislación Aplicable
Estos Términos se rigen por las leyes de la República de Chile.

16. Modificaciones
Podemos modificar estos Términos en cualquier momento. Los cambios se aplican desde su publicación en el Sitio y no afectan las compras ya realizadas.

17. Contacto
Para consultas sobre estos Términos: apolovibes3d@gmail.com`,
  },
  privacidad: {
    titulo: 'Política de Privacidad',
    actualizacion: fechaLegalLarga(),
    texto:
      `1. Responsable del Tratamiento
El responsable de sus datos personales es Apolo Vibes SPA, con domicilio en calle Pasaje el Boldo Nro:33, Viña del Mar, Chile. Contacto: apolovibes3d@gmail.com.

2. Datos que Recopilamos
- Datos de identificación y contacto: nombre, apellidos, RUT, correo y teléfono.
- Datos de envío: región, comuna, ciudad, dirección, número, departamento y código postal.
- Datos de pedidos y cotizaciones: productos, montos, tipo de documento tributario (boleta o factura) y comunicaciones con nosotros.
- Datos de facturación, si solicita factura: RUT, razón social y giro.
- Reseñas que publique: calificación, comentario y nombre de autor, que se muestran públicamente en la ficha del producto.
- Contenido que ingresa en el cotizador: descripciones e imágenes del diseño.
- Datos de pago: se procesan directamente en Tuu; nosotros no almacenamos los datos de su tarjeta, solo el identificador de la transacción y su estado.
- Datos de autenticación: contraseña almacenada con hash y, si activa la verificación en dos pasos, el secreto de la aplicación de autenticación y los códigos de respaldo.
- Datos de su cuenta de Google, si inicia sesión con Google: nombre, apellido y correo.
- Datos técnicos y de seguridad: dirección IP, tipo de navegador, fecha y hora de acceso, e historial de inicios de sesión y eventos de seguridad.

3. Para Qué los Usamos y Con Qué Fundamento
- Procesar y entregar sus pedidos y cotizaciones (necesario para ejecutar el contrato).
- Enviarle por correo el comprobante y los avisos sobre su pedido (ejecución del contrato).
- Atender consultas, garantías y reclamos (ejecución del contrato y obligaciones legales).
- Cumplir obligaciones tributarias y contables (obligación legal).
- Mantener la seguridad de su cuenta y prevenir fraudes o accesos no autorizados (interés legítimo).
- Publicar las reseñas que usted envía sobre productos comprados (con su consentimiento al enviarlas).
- Mejorar el Sitio (interés legítimo).
Actualmente no enviamos boletines ni promociones por correo. Si lo hacemos en el futuro, será solo con su consentimiento previo, que podrá retirar cuando quiera.

4. Uso de Herramientas Automatizadas
Para estimar cotizaciones, las imágenes y descripciones que usted envía se procesan mediante un servicio de estimación automatizada que calcula materiales y precio. No lo use para enviar datos sensibles o de otras personas. Usamos ese contenido solo para prestarle el servicio solicitado. La generación de diseños 3D con inteligencia artificial no está habilitada actualmente.

5. Con Quién Compartimos sus Datos
No vendemos sus datos personales. Los compartimos solo con proveedores que los necesitan para prestarnos el servicio (encargados del tratamiento):
- Proveedores de pago (Tuu).
- Empresas de transporte y envío (Starken).
- Proveedores de alojamiento web y de correo transaccional.
- Servicio de estimación automatizada de cotizaciones.
- Proveedores de autenticación (Google), si inicia sesión con su cuenta.
- Proveedores de verificación de seguridad (Google reCAPTCHA).
También podemos comunicarlos cuando lo exija la ley o una autoridad competente.

6. Transferencias Internacionales
Algunos de estos proveedores pueden almacenar o procesar datos fuera de Chile. En esos casos exigimos medidas de protección adecuadas conforme a la ley.

7. Cookies
Usamos solo cookies esenciales para el funcionamiento del Sitio y no utilizamos cookies de analítica, publicidad ni seguimiento. Puede configurar su navegador para rechazarlas, aunque algunas funciones, como mantener la sesión o completar un pago, dejarían de funcionar. El detalle está en nuestra Política de Cookies.

8. Cuánto Tiempo Conservamos sus Datos
- Datos de su cuenta: mientras la cuenta esté activa.
- Datos de pedidos y documentos tributarios: 6 años, por obligaciones legales.
- Cotizaciones que no se concretan: 12 meses.
- Registros de seguridad: durante el tiempo necesario para prevenir fraudes y atender reclamos.
Una vez cumplidos esos plazos, eliminamos o anonimizamos los datos. No usamos sus datos para marketing, por lo que no mantenemos información con esa finalidad.

9. Seguridad
Aplicamos medidas técnicas y organizativas razonables para proteger sus datos contra acceso no autorizado, pérdida o alteración. Las contraseñas se almacenan con hash, ofrecemos verificación en dos pasos y usamos reCAPTCHA en el registro y el inicio de sesión. Si ocurre una brecha de seguridad que afecte sus datos, actuaremos y notificaremos según lo exige la ley.

10. Sus Derechos
Usted puede solicitar el acceso, la rectificación, la supresión, la oposición al tratamiento, la portabilidad de sus datos y el bloqueo temporal, además de retirar su consentimiento en cualquier momento. Para ejercer estos derechos, escríbanos a apolovibes3d@gmail.com indicando su nombre y qué solicita. Le responderemos dentro de los plazos legales. Si considera que no atendimos su solicitud, puede reclamar ante la autoridad de protección de datos competente.

11. Menores de Edad
El Sitio no está dirigido a menores de 18 años y no recopilamos intencionalmente sus datos personales.

12. Cambios en esta Política
Podemos actualizar esta Política. Publicaremos los cambios en esta página con la fecha de última actualización.

13. Contacto
- Correo: apolovibes3d@gmail.com
- Dirección: calle Pasaje el Boldo Nro:33, Viña del Mar, Chile.`,
  },
  cambios: {
    titulo: 'Cambios y Devoluciones',
    actualizacion: fechaLegalLarga(),
    texto:
      `1. Alcance
Esta política explica cómo solicitar un cambio, una devolución o hacer efectiva la garantía legal de los productos comprados en Apolo Vibes 3D. Se aplica junto con nuestros Términos y Condiciones y no reemplaza ni limita los derechos que la Ley 19.496 reconoce a los consumidores.

2. Plazos para Solicitar un Cambio
Puede solicitar el cambio de un producto por otro modelo, color o variante dentro de 10 días corridos contados desde la recepción del pedido, siempre que el producto esté sin uso, completo y con su embalaje original. El cambio está sujeto a disponibilidad de stock y a la diferencia de precio que corresponda.

3. Productos Personalizados
Los productos confeccionados según las especificaciones del cliente o claramente personalizados (por ejemplo, diseños a medida o piezas basadas en una referencia aprobada) no admiten cambio por elección del cliente. Si el producto llega con fallas, daños o no corresponde a lo aprobado, aplica la garantía legal.

4. Derecho de Retracto
En las compras realizadas a través del Sitio, usted puede arrepentirse dentro de 10 días contados desde la recepción del producto, sin necesidad de expresar causa, conforme a la Ley 19.496. Para ejercerlo, escríbanos a apolovibes3d@gmail.com indicando su número de pedido. El producto debe devolverse sin uso, completo y con su embalaje original. Le reembolsaremos el precio pagado por el mismo medio de pago, dentro del plazo legal. Los costos de devolución serán de cargo del cliente.
El retracto no aplica a productos confeccionados según las especificaciones del cliente o claramente personalizados, ni a los demás casos de exclusión que establece la ley.

5. Devoluciones por Garantía Legal
Si un producto presenta fallas o defectos, o no es apto para su uso, usted tiene derecho a la garantía legal de 6 meses desde la recepción del producto (para productos nuevos). Puede elegir la reposición del producto o la devolución de lo pagado, en los términos de los artículos 19 a 21 de la Ley 19.496.
Para solicitarla, escríbanos a apolovibes3d@gmail.com con su número de pedido y, si es posible, fotografías del problema. Revisaremos el caso y le responderemos dentro de 2 días hábiles. No se aplica cuando el defecto se debe a mal uso, manipulación indebida o desgaste normal.

6. Productos Dañados en el Transporte
Si su pedido llega dañado, repórtelo dentro de 48 horas desde la entrega a apolovibes3d@gmail.com con su número de pedido y fotografías del embalaje y del producto. Coordinaremos el reemplazo o la solución que corresponda con la empresa de transporte. Este plazo es solo para agilizar el reclamo al transporte y no limita su garantía legal.

7. Cómo Solicitar un Cambio o Devolución
Escríbanos a apolovibes3d@gmail.com indicando:
- Nombre completo y número de pedido.
- Producto que desea cambiar o devolver.
- Motivo de la solicitud.
- Fotografías del producto y de su embalaje, cuando corresponda.
Le confirmaremos por correo si la solicitud es aceptada y le indicaremos la forma de envío. No envíe productos sin antes recibir nuestra confirmación.

8. Costos de Envío
En los cambios por elección del cliente y en las devoluciones por retracto, el costo del envío de retorno es de cargo del cliente. Si la devolución se debe a un error nuestro, a un producto defectuoso o al ejercicio de la garantía legal, asumimos el costo del envío.

9. Reembolsos
Los reembolsos se realizan por el mismo medio de pago utilizado en la compra, dentro del plazo legal desde que confirmamos la devolución. Si el pago se realizó con tarjeta, el abono puede tardar algunos días en reflejarse según los plazos del banco o de la plataforma de pago.

10. Contacto
Para consultas sobre cambios, devoluciones o garantías: apolovibes3d@gmail.com`,
  },
  cookies: {
    titulo: 'Política de Cookies',
    actualizacion: fechaLegalLarga(),
    texto:
      `1. Qué son las Cookies
Las cookies son pequeños archivos que el navegador guarda en su dispositivo cuando visita un sitio web. Permiten recordar información sobre su visita, como su sesión o sus preferencias. También usamos tecnologías equivalentes, como el almacenamiento local del navegador (localStorage y sessionStorage), que cumplen una función similar.

2. Cookies Propias
El Sitio utiliza únicamente estas cookies, todas necesarias para su funcionamiento. Los nombres técnicos van entre paréntesis para que pueda identificarlas si alguna vez necesita eliminarlas desde su navegador:
- Cookie de sesión: mantiene su sesión iniciada y renueva el acceso sin volver a pedirle sus datos. Dura mientras el navegador está abierto y no puede ser leída por el código del Sitio, solo por nuestros servidores.
- Cookie de verificación en dos pasos: recuerda, por un máximo de 5 minutos, que ya completó el segundo paso del inicio de sesión cuando su cuenta tiene activada la autenticación de dos factores.
Ninguna de estas cookies se usa para publicidad ni para seguimiento.

3. Almacenamiento Local
Además de las cookies, el navegador guarda información en su dispositivo:
- Sesión iniciada: guarda el token de acceso y los datos básicos de su cuenta para no pedirle que ingrese en cada visita.
- Tema visual: su preferencia de tema claro u oscuro.
- Avisos de seguridad: recuerdan, solo mientras la pestaña está abierta, que hay una verificación en dos pasos pendiente o un aviso de seguridad por mostrar.
El carrito de compras no se guarda en su navegador: se almacena en su cuenta en nuestros servidores.

4. Cookies de Terceros
Algunas funciones cargan servicios de terceros que pueden instalar sus propias cookies o recibir datos técnicos como su dirección IP, regidos por sus políticas de privacidad:
- Tuu: al confirmar el pago, lo redirigimos a su plataforma para procesar la transacción.
- Google: si elige iniciar sesión con su cuenta de Google, si el navegador carga las tipografías del Sitio desde Google Fonts, o cuando se muestra el reCAPTCHA en el registro y el inicio de sesión.
No utilizamos cookies de analítica, publicidad, redes sociales ni píxeles de seguimiento. Por eso el Sitio no muestra un banner de consentimiento de cookies.

5. Cómo Gestionar las Cookies
Puede eliminar o bloquear las cookies y el almacenamiento local desde la configuración de su navegador (Chrome, Edge, Firefox o Safari). Si bloquea las cookies propias, no podrá mantener su sesión iniciada, usar la autenticación de dos factores ni completar un pago.

6. Base Legal
Tratamos los datos obtenidos a través de cookies conforme a nuestra Política de Privacidad y a la Ley 19.496 y la normativa chilena de protección de datos personales, incluidas las disposiciones de la Ley 21.719 que se encuentren vigentes.

7. Cambios en esta Política
Podemos actualizar esta Política cuando incorporemos nuevas cookies o cambie la normativa aplicable. Publicaremos la versión vigente en esta página con su fecha de actualización.

8. Contacto
Para consultas sobre el uso de cookies: apolovibes3d@gmail.com`,
  },
}

const overlayStyle = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(0,0,0,.55)', backdropFilter: 'blur(4px)', padding: 20,
}

const modalStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--line)',
  borderRadius: 20,
  boxShadow: '0 20px 60px rgba(0,0,0,.3)',
  position: 'relative',
  width: '100%',
  maxWidth: 700,
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
}

const cerrarStyle = {
  position: 'absolute', top: 16, right: 18, zIndex: 2,
  background: 'none', border: 'none', color: 'var(--text-dim)',
  cursor: 'pointer', padding: 4, borderRadius: 6, lineHeight: 1,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}

function ContenidoLegal({ titulo, actualizacion, texto, onClose }) {
  useBloqueoScroll()

  useEffect(() => {
    const alPresionarTecla = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', alPresionarTecla)
    return () => window.removeEventListener('keydown', alPresionarTecla)
  }, [onClose])

  return createPortal(
    <div style={overlayStyle} onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="legal-modal-titulo"
        style={modalStyle}
        onClick={(e) => e.stopPropagation()}
      >
        <style>{`
          .modal-scroll::-webkit-scrollbar { width: 6px; }
          .modal-scroll::-webkit-scrollbar-track { background: transparent; margin: 8px 0; }
          .modal-scroll::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
          .modal-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
          .modal-scroll { scrollbar-gutter: stable; }
        `}</style>

        {/* Header */}
        <div style={{
          flexShrink: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 10,
          padding: '15px 52px 13px', background: 'var(--surface)',
          borderBottom: '1px solid var(--line)',
        }}>
          <img
            src={mediaPath('politicasSeguridad.webp')}
            alt="Políticas Apolo Vibes"
            loading="lazy"
            decoding="async"
            width="512"
            height="468"
            style={{ height: 100, width: 'auto', marginBottom: -10 }}
          />
          <h2 id="legal-modal-titulo" style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: 0, color: 'var(--text)' }}>
            {titulo}
          </h2>
          <p style={{ fontSize: 12, margin: '-4px 0 0', color: 'var(--text-dim)', textAlign: 'center' }}>
            Última actualización: {actualizacion}
          </p>
          <button type="button" onClick={onClose} aria-label="Cerrar" style={cerrarStyle}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div
          className="modal-scroll"
          style={{
            padding: '20px 24px', overflowY: 'auto', flex: 1, minHeight: 0,
            fontSize: 14, lineHeight: 1.7, color: 'var(--text-dim)',
            whiteSpace: 'pre-wrap',
          }}
        >
          {texto}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px', borderTop: '1px solid var(--line)',
          display: 'flex', justifyContent: 'flex-end',
        }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'var(--accent)', color: '#fff',
              border: 'none', borderRadius: 10, padding: '10px 24px',
              fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Entendido
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default function LegalModal({ tipo, onClose }) {
  const contenido = CONTENT[tipo]
  if (!contenido) return null

  return (
    <ContenidoLegal
      titulo={contenido.titulo}
      actualizacion={contenido.actualizacion}
      texto={contenido.texto}
      onClose={onClose}
    />
  )
}
