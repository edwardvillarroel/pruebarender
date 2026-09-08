import { X } from 'lucide-react'

const CONTENT = {
  terminos: {
    titulo: 'Términos y Condiciones',
    texto: `Última actualización: 30 de agosto de 2026

1. Aceptación de los Términos
Al acceder y utilizar el sitio web de Apolo Vibes 3D (en adelante, "el Sitio"), usted acepta los presentes Términos y Condiciones en su totalidad. Si no está de acuerdo con alguno de estos términos, le solicitamos no utilice el Sitio.

2. Descripción del Servicio
Apolo Vibes 3D es una tienda en línea especializada en la venta de figuras de colección impresas en 3D, impresoras de resina, filamentos, resinas, repuestos y diseños personalizados. Nos reservamos el derecho de modificar, suspender o discontinuar cualquier aspecto del servicio en cualquier momento y sin previo aviso.

3. Productos y Precios
Todos los productos exhibidos en el Sitio están sujetos a disponibilidad. Los precios están expresados en pesos chilenos (CLP) e incluyen IVA, salvo indicación contraria. Nos reservamos el derecho de cambiar los precios sin previo aviso. Las imágenes de los productos son referenciales y pueden diferir ligeramente del producto final.

4. Pedidos y Cotizaciones
Los pedidos realizados a través del Sitio están sujetos a confirmación de stock y disponibilidad. Las cotizaciones generadas mediante la herramienta de IA son estimaciones y pueden variar según la complejidad final del diseño, materiales utilizados y condiciones de fabricación. El precio definitivo será confirmado por nuestro equipo antes de proceder con la producción.

5. Formas de Pago
Aceptamos los medios de pago disponibles en la plataforma de checkout, incluyendo tarjetas de crédito y débito a través de Webpay y Tuu. El procesamiento de pagos está sujeto a las políticas de los proveedores de servicios de pago.

6. Envíos y Entregas
Los tiempos de entrega son estimados y pueden variar según la ubicación, la disponibilidad del producto y la complejidad de los pedidos personalizados. Apolo Vibes 3D no se hace responsable por demoras ocasionadas por terceros transportistas.

7. Pedidos Personalizados
Los diseños a medida cotizados a través de nuestra herramienta de generación de modelos 3D con IA son orientativos. El producto final puede diferir de la visualización generada. Se procederá a la fabricación una vez aprobado el diseño definitivo por el cliente y confirmado el pago.

8. Propiedad Intelectual
Todo el contenido del Sitio, incluyendo pero no limitado a textos, gráficos, logotipos, imágenes, modelos 3D y software, es propiedad de Apolo Vibes 3D o de sus proveedores de contenido y está protegido por las leyes de propiedad intelectual chilenas e internacionales.

9. Limitación de Responsabilidad
Apolo Vibes 3D no será responsable por daños indirectos, incidentales, especiales o consecuentes que resulten del uso o la imposibilidad de usar el Sitio o los productos adquiridos. Nuestra responsabilidad máxima será en todo caso el monto pagado por el producto en cuestión.

10. Legislación Aplicable
Los presentes Términos y Condiciones se rigen por las leyes de la República de Chile. Cualquier disputa será sometida a la jurisdicción de los tribunales competentes de Valparaíso, Chile.

11. Modificaciones
Nos reservamos el derecho de modificar estos Términos y Condiciones en cualquier momento. Las modificaciones entrarán en vigor inmediatamente después de su publicación en el Sitio. El uso continuado del Sitio después de dichas modificaciones constituye la aceptación de los mismos.

12. Contacto
Para consultas sobre estos Términos y Condiciones, puede contactarnos a través de correo@gmail.com.`,
  },
  privacidad: {
    titulo: 'Política de Privacidad',
    texto: `Última actualización: 30 de agosto de 2026

1. Información que Recopilamos
En Apolo Vibes 3D recopilamos información que usted nos proporciona directamente al realizar pedidos, cotizaciones o contactarnos, incluyendo:
• Nombre y apellidos
• Correo electrónico
• Número de teléfono
• Dirección de envío
• Datos de pago procesados a través de nuestros proveedores de pago

También recopilamos información automáticamente cuando utiliza el Sitio, como dirección IP, tipo de navegador, páginas visitadas y tiempo de permanencia.

2. Uso de la Información
Utilizamos la información recopilada para:
• Procesar y fulfillar sus pedidos
• Enviar confirmaciones, actualizaciones de pedido y notificaciones relevantes
• Responder a sus consultas y solicitudes de cotización
• Mejorar nuestro Sitio, productos y servicios
• Enviar comunicaciones de marketing, solo si usted ha dado su consentimiento
• Cumplir con obligaciones legales

3. Compartición de Información
No vendemos ni compartimos su información personal con terceros, excepto en los siguientes casos:
• Proveedores de servicios de pago (Webpay, Tuu) para procesar transacciones
• Servicios de envío para entregar sus pedidos
• Cuando lo requiera la ley o una orden judicial

4. Cookies y Tecnologías de Rastreo
El Sitio utiliza cookies para mejorar su experiencia de navegación. Puede configurar su navegador para rechazar cookies, aunque esto podría afectar la funcionalidad del Sitio.

5. Seguridad de los Datos
Implementamos medidas de seguridad técnicas y organizativas razonables para proteger su información personal contra acceso no autorizado, alteración, divulgación o destrucción. Sin embargo, ningún método de transmisión por Internet o almacenamiento electrónico es 100% seguro.

6. Retención de Datos
Conservamos su información personal solo durante el tiempo necesario para los fines para los que fue recopilada, o según lo requiera la legislación aplicable.

7. Sus Derechos
Usted tiene derecho a:
• Acceder a su información personal
• Solicitar la corrección de datos inexactos
• Solicitar la eliminación de su información personal
• Oponerse al procesamiento de sus datos
• Solicitar la portabilidad de sus datos
• Retirar su consentimiento en cualquier momento

Para ejercer estos derechos, contáctenos a través de correo@gmail.com.

8. Menores de Edad
El Sitio no está dirigido a menores de 18 años. No recopilamos intencionalmente información personal de menores de edad.

9. Cambios en esta Política
Nos reservamos el derecho de modificar esta Política de Privacidad en cualquier momento. Los cambios serán publicados en esta página con la fecha de última actualización.

10. Contacto
Si tiene preguntas sobre esta Política de Privacidad, puede contactarnos a través de:
• Correo electrónico: correo@gmail.com
• Teléfono: +569xxxxxxxx
• Dirección: Viña del Mar, Chile`,
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
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '20px 24px', borderBottom: '1px solid var(--line)',
        }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, margin: 0, color: 'var(--text)' }}>{titulo}</h2>
          <button
            onClick={onClose}
            style={{
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
