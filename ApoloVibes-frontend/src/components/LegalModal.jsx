import { X } from 'lucide-react'
import { mediaPath } from '../utils/media.js'
import { fechaLegalLarga } from '../services/legal.js'

const CONTENT = {
  terminos: {
    titulo: 'Términos y Condiciones',
    texto: `Última actualización: ${fechaLegalLarga()}

1. Identificación del Proveedor
El sitio de Apolo Vibes 3D es operado por Apolo Vibes SPA, RUT: 78.064.166-5 con domicilio en calle Pasaje el Boldo Nro:33, Viña del Mar, Chile. Puede contactarnos en pabla.rojas@hotmail.com.

2. Aceptación de los Términos
Al acceder y utilizar el Sitio, usted acepta estos Términos y Condiciones. Si no está de acuerdo con ellos, le solicitamos no utilizar el Sitio.

3. Descripción del Servicio
Apolo Vibes 3D es una tienda en línea de figuras de colección impresas en 3D, impresoras de resina y diseños personalizados. Podemos modificar o discontinuar aspectos del servicio, sin que ello afecte los pedidos ya confirmados.

4. Productos y Precios
Los productos están sujetos a disponibilidad. Los precios se expresan en pesos chilenos (CLP) e incluyen IVA. El precio que se respeta es el vigente al momento de confirmar su pedido; los cambios de precio solo afectan compras futuras. Las imágenes son referenciales y pueden diferir ligeramente del producto final.

5. Pedidos, Confirmación y Cotizaciones
Los pedidos están sujetos a confirmación de stock. Si un producto pagado no estuviera disponible, se lo informaremos y le devolveremos el dinero por el mismo medio de pago. Tras su compra le enviaremos por correo una confirmación con el detalle del pedido.
Las cotizaciones generadas con la herramienta de IA son estimaciones y pueden variar según la complejidad del diseño, los materiales y las condiciones de fabricación. El precio definitivo será confirmado por nuestro equipo antes de producir.

6. Formas de Pago
Aceptamos los medios de pago disponibles en el checkout, incluyendo tarjetas de crédito y débito a través de la plataforma Tuu. El procesamiento de pagos está sujeto a las políticas de esos proveedores. Apolo Vibes 3D no almacena los datos de su tarjeta.

7. Envíos y Entregas
Los plazos de entrega se informan durante la compra y pueden variar según la ubicación y la complejidad de los pedidos personalizados. Trabajamos con servicios de transporte externos, pero somos responsables frente a usted por la entrega de su pedido. Si hay retrasos, se lo comunicaremos y podrá ejercer los derechos que le reconoce la ley.

8. Derecho de Retracto
De acuerdo con la Ley 19.496, en las compras realizadas a través del Sitio usted puede arrepentirse dentro de 10 días contados desde la recepción del producto, sin necesidad de expresar causa.
Para ejercerlo, escríbanos a [correo] indicando su número de pedido. El producto debe devolverse [sin uso, completo y con su embalaje original]. Le reembolsaremos el precio pagado por el mismo medio de pago, dentro del plazo legal. Los costos de devolución serán [de cargo del cliente / de cargo de Apolo Vibes 3D].
El retracto no aplica a productos confeccionados según las especificaciones del cliente o claramente personalizados (por ejemplo, diseños a medida), ni a los demás casos de exclusión que establece la ley.
Ejercer o no el retracto no afecta su derecho a la garantía legal.

9. Garantía Legal
Si un producto presenta fallas o defectos, o no es apto para su uso, usted tiene derecho a la garantía legal de 6 meses desde la recepción del producto (para productos nuevos). Puede elegir entre la reparación gratuita, la reposición del producto o la devolución de lo pagado, en los términos de los artículos 19 a 21 de la Ley 19.496.
Para solicitarla, escríbanos a pabla.rojas@hotmail.com con su número de pedido y, si es posible, fotografías del problema. No se aplica cuando el defecto se debe a mal uso, manipulación indebida o desgaste normal.

10. Pedidos Personalizados y Cancelación
Los diseños a medida, incluidos los generados con nuestra herramienta de IA, son orientativos: el producto final puede diferir de la visualización generada. La fabricación comienza una vez aprobado el diseño definitivo y confirmado el pago.
Puede cancelar un pedido personalizado sin costo antes de que comience la producción. Una vez iniciada, podremos cobrar los costos de materiales y trabajo ya incurridos. Si el producto llega con fallas, aplica la garantía legal.

11. Contenido y Diseños Aportados por el Cliente
Si usted nos envía imágenes, modelos o ideas para un pedido personalizado, declara ser su titular o contar con las autorizaciones necesarias. Nos reservamos el derecho de rechazar pedidos que infrinjan derechos de autor, marcas u otros derechos de terceros. Usted nos autoriza a usar ese contenido solo para cotizar y fabricar su pedido.

12. Propiedad Intelectual
Los textos, gráficos, logotipos, imágenes, modelos 3D y software del Sitio son propiedad de Apolo Vibes 3D o de sus proveedores y están protegidos por la legislación chilena e internacional.

13. Responsabilidad
Apolo Vibes 3D responde en los términos que establece la ley. Nada en estos Términos limita o excluye los derechos irrenunciables que la Ley 19.496 reconoce a los consumidores.

14. Reclamos y Solución de Controversias
Si tiene un problema, escríbanos primero a pabla.rojas@hotmail.com y buscaremos una solución. También puede acudir al SERNAC o al Juzgado de Policía Local competente, conforme a la Ley 19.496.

15. Legislación Aplicable
Estos Términos se rigen por las leyes de la República de Chile.

16. Modificaciones
Podemos modificar estos Términos en cualquier momento. Los cambios se aplican desde su publicación en el Sitio y no afectan las compras ya realizadas.

17. Contacto
Para consultas sobre estos Términos: pabla.rojas@hotmail.com.`,
  },
  privacidad: {
    titulo: 'Política de Privacidad',
    texto: `Última actualización: ${fechaLegalLarga()}

1. Responsable del Tratamiento
El responsable de sus datos personales es Apolo Vibes SPA, con domicilio en calle Pasaje el Boldo Nro:33, Viña del Mar, Chile. Contacto: pabla.rojas@hotmail.com.

2. Datos que Recopilamos
- Datos de identificación y contacto: nombre, apellidos, correo y teléfono.
- Datos de envío: dirección de entrega.
- Datos de pedidos y cotizaciones: productos, montos y comunicaciones con nosotros.
- Contenido que ingresa en la herramienta de diseño con IA: textos, descripciones e imágenes.
- Datos de pago: se procesan directamente por Tuu; nosotros no almacenamos los datos de su tarjeta.
- Datos técnicos: dirección IP, tipo de navegador, páginas visitadas y tiempo de permanencia.

3. Para Qué los Usamos y Con Qué Fundamento
- Procesar y entregar sus pedidos y cotizaciones (necesario para ejecutar el contrato).
- Enviar confirmaciones y avisos sobre su pedido (ejecución del contrato).
- Atender consultas, garantías y reclamos (ejecución del contrato y obligaciones legales).
- Cumplir obligaciones tributarias y contables (obligación legal).
- Mejorar el Sitio y prevenir fraudes (interés legítimo).
- Enviarle novedades y promociones (solo con su consentimiento, que puede retirar cuando quiera).

4. Uso de Herramientas de Inteligencia Artificial
Para generar diseños y cotizaciones, el contenido que usted ingresa se procesa mediante servicios de IA de terceros. No lo use para enviar datos sensibles o de otras personas. Usamos ese contenido solo para prestarle el servicio solicitado.

5. Con Quién Compartimos sus Datos
No vendemos sus datos personales. Los compartimos solo con proveedores que los necesitan para prestarnos el servicio (encargados del tratamiento):
- Proveedores de pago (Tuu).
- Empresas de transporte y envío.
- Proveedores de alojamiento del Sitio, correo electrónico y analítica: [indicar cuáles].
- Proveedores de servicios de IA: [indicar cuáles].
También podemos comunicarlos cuando lo exija la ley o una autoridad competente.

6. Transferencias Internacionales
Algunos de estos proveedores pueden almacenar o procesar datos fuera de Chile. En esos casos exigimos medidas de protección adecuadas conforme a la ley.

7. Cookies
Usamos cookies esenciales para el funcionamiento del Sitio. Las cookies de analítica o marketing solo se activan con su consentimiento. Puede configurar su navegador para rechazarlas, aunque algunas funciones del Sitio podrían verse afectadas.

8. Cuánto Tiempo Conservamos sus Datos
- Datos de pedidos y documentos tributarios: 6 años, por obligaciones legales.
- Cotizaciones que no se concretan: [12 meses].
- Datos de marketing: hasta que retire su consentimiento.
Luego los eliminamos o anonimizamos.

9. Seguridad
Aplicamos medidas técnicas y organizativas razonables para proteger sus datos contra acceso no autorizado, pérdida o alteración. Si ocurre una brecha de seguridad que afecte sus datos, actuaremos y notificaremos según lo exige la ley.

10. Sus Derechos
Usted puede solicitar el acceso, la rectificación, la supresión, la oposición al tratamiento, la portabilidad de sus datos y el bloqueo temporal, además de retirar su consentimiento en cualquier momento. Para ejercer estos derechos, escríbanos a [correo] indicando su nombre y qué solicita. Le responderemos dentro de los plazos legales. Si considera que no atendimos su solicitud, puede reclamar ante la autoridad de protección de datos competente.

11. Menores de Edad
El Sitio no está dirigido a menores de 18 años y no recopilamos intencionalmente sus datos personales.

12. Cambios en esta Política
Podemos actualizar esta Política. Publicaremos los cambios en esta página con la fecha de última actualización.

13. Contacto
- Correo: pabla.rojas@hotmail.com
- Dirección: calle Pasaje el Boldo Nro:33, Viña del Mar, Chile.`,
  },
}

export default function LegalModal({ tipo, onClose }) {
  if (!tipo || !CONTENT[tipo]) return null
  const { titulo, texto } = CONTENT[tipo]

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--line)',
          borderRadius: 16,
          width: '90%',
          maxWidth: 700,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          position: 'sticky', top: 0, zIndex: 3,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 10,
          padding: '15px 52px 13px', background: 'var(--surface)',
          borderBottom: '1px solid var(--line)',
        }}>
          <img src={mediaPath('apolo-vibes-logo.png')} alt="Logo" style={{ height: 60, width: 'auto', marginBottom: -10 }} />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: 0, color: 'var(--text)' }}>{titulo}</h2>
          <button
            onClick={onClose}
            style={{
              position: 'absolute', top: 12, right: 12,
              background: 'none', border: 'none', color: 'var(--text-dim)',
              cursor: 'pointer', padding: 4, borderRadius: 6,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div style={{
          padding: '20px 24px', overflowY: 'auto', flex: 1,
          fontSize: 14, lineHeight: 1.7, color: 'var(--text-dim)',
          whiteSpace: 'pre-wrap',
        }}>
          {texto}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px', borderTop: '1px solid var(--line)',
          display: 'flex', justifyContent: 'flex-end',
        }}>
          <button
            onClick={onClose}
            style={{
              background: 'var(--accent)', color: '#fff',
              border: 'none', borderRadius: 8, padding: '10px 24px',
              fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  )
}
