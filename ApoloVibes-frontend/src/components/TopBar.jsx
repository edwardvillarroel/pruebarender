import { useState, useEffect, useRef } from 'react'
import { Truck } from 'lucide-react'

const ALTO_BARRA = 40

// Debe ser MAYOR que ALTO_BARRA. La barra vive en el flujo del documento
// (position: relative), asi que al ocultarse le saca ALTO_BARRA px de alto a
// toda la pagina. Cerca del final, el navegador recorta scrollY para compensar
// y eso vuelve como un evento de scroll con el signo invertido: la barra cree
// que el usuario subio, se vuelve a mostrar, el documento crece, se recorta
// otra vez... y la pagina rebota sola, indefinidamente. Con el umbral por
// encima de ALTO_BARRA, ningun scroll puede ser rechazado por ser el eco de
// nuestra propia animacion, y el lazo no puede arrancar.
const UMBRAL_SCROLL = 60

export default function TopBar() {
  const [oculto, setOculto] = useState(false)
  const ultimaPos = useRef(0)
  // Espejo del estado en un ref: el listener de scroll se registra una sola vez
  // y asi no depende de un closure con el valor viejo de `oculto`.
  const ocultoRef = useRef(false)

  useEffect(() => {
    const alScrollear = () => {
      const y = window.scrollY
      const delta = y - ultimaPos.current
      ultimaPos.current = y

      if (y <= UMBRAL_SCROLL) {
        if (ocultoRef.current) {
          ocultoRef.current = false
          setOculto(false)
        }
        return
      }
      if (Math.abs(delta) < UMBRAL_SCROLL) return

      const nuevo = delta > 0
      if (nuevo === ocultoRef.current) return
      ocultoRef.current = nuevo
      setOculto(nuevo)
    }
    alScrollear()
    window.addEventListener('scroll', alScrollear, { passive: true })
    return () => window.removeEventListener('scroll', alScrollear)
  }, [])

  return (
    <div
      style={{
        position: 'relative',
        background: 'var(--surface)',
        color: '#EDEDE5',
        overflow: 'hidden',
        maxHeight: oculto ? 0 : ALTO_BARRA,
        opacity: oculto ? 0 : 1,
        transition: 'max-height .35s ease, opacity .3s ease',
        zIndex: 95,
      }}
    >
      <div
        className="wrap"
        style={{
          height: ALTO_BARRA,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          textAlign: 'center',
          whiteSpace: 'nowrap',
        }}
      >
        <Truck size={14} color="var(--accent)" style={{ flexShrink: 0 }} />
        <p style={{ fontSize: 12.5, letterSpacing: '.02em', margin: 0 }}>
          <span style={{ color: 'var(--accent)', fontWeight: 700 }}>Envíos a todo Chile</span> en compras sobre $50.000 | Retiro en lugar de entrega acordado
        </p>
      </div>
    </div>
  )
}