import { useState, useEffect, useRef } from 'react'
import { Truck } from 'lucide-react'

export default function TopBar() {
  const [oculto, setOculto] = useState(false)
  const ultimaPos = useRef(0)

  useEffect(() => {
    const alScrollear = () => {
      const y = window.scrollY
      const delta = y - ultimaPos.current
      ultimaPos.current = y
      if (y <= 40) {
        setOculto(false)
        return
      }
      if (Math.abs(delta) < 10) return
      setOculto(delta > 0)
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
        maxHeight: oculto ? 0 : 40,
        opacity: oculto ? 0 : 1,
        transition: 'max-height .35s ease, opacity .3s ease',
        zIndex: 95,
      }}
    >
      <div
        className="wrap"
        style={{
          height: 40,
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