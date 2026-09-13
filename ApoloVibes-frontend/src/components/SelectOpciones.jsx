import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../context/ThemeContext.jsx'
import { ChevronDown } from 'lucide-react'

// Dropdown custom reutilizable: las opciones se despliegan pegadas al campo,
// como una extensión visual del input (mismo ancho, mismo borde).
// Soporta placeholder (valor vacío), estado deshabilitado y listas largas con scroll.
export default function SelectOpciones({
  id,
  options,
  value,
  onChange,
  placeholder = 'Selecciona una opción',
  disabled = false,
}) {
  const { theme } = useTheme()
  const [abierto, setAbierto] = useState(false)
  const contRef = useRef(null)

  useEffect(() => {
    function clickFuera(e) {
      if (contRef.current && !contRef.current.contains(e.target)) setAbierto(false)
    }
    function tecla(e) {
      if (e.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('mousedown', clickFuera)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', clickFuera)
      document.removeEventListener('keydown', tecla)
    }
  }, [])

  // Si el campo se deshabilita, cerrar el menú
  useEffect(() => {
    if (disabled) setAbierto(false)
  }, [disabled])

  const esOscuro = theme === 'dark'
  const fondo = esOscuro ? 'var(--surface)' : 'var(--bg)'
  const texto = esOscuro ? 'var(--text)' : 'var(--surface)'
  const lista = options || []
  const valores = lista.map(o => (typeof o === 'string' ? o : o.value))
  const sinSeleccion = value == null || !valores.includes(value)
  const opSeleccionada = lista.find(o => (typeof o === 'string' ? o : o.value) === value)
  const etiquetaSeleccion = opSeleccionada
    ? (typeof opSeleccionada === 'string' ? opSeleccionada : opSeleccionada.label)
    : ''

  return (
    <div ref={contRef} style={{ position: 'relative' }}>
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => setAbierto(a => !a)}
        aria-haspopup="listbox"
        aria-expanded={abierto && !disabled}
        aria-disabled={disabled}
        style={{
          width: '100%',
          fontFamily: 'var(--font-body)',
          background: fondo,
          border: `1px solid ${abierto ? 'var(--gold)' : 'var(--line)'}`,
          color: sinSeleccion ? 'var(--text-dim)' : texto,
          borderRadius: abierto ? '8px 8px 0 0' : 8,
          padding: '10px 12px',
          fontSize: 14,
          textAlign: 'left',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? .45 : 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        {sinSeleccion ? placeholder : etiquetaSeleccion}
        <ChevronDown
          size={16}
          style={{ flexShrink: 0, transition: 'transform .15s', transform: abierto ? 'rotate(180deg)' : undefined }}
        />
      </button>

      {abierto && !disabled && (
        <ul
          role="listbox"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            margin: 0,
            padding: 0,
            listStyle: 'none',
            background: fondo,
            border: '1px solid var(--gold)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            overflow: 'hidden',
            zIndex: 40,
            boxShadow: '0 10px 24px rgba(0,0,0,.15)',
            maxHeight: 220,
            overflowY: 'auto',
          }}
        >
          {lista.map(op => {
            const valor = typeof op === 'string' ? op : op.value
            const etiqueta = typeof op === 'string' ? op : op.label
            const seleccionado = valor === value
            return (
              <li key={valor} role="option" aria-selected={seleccionado}>
                <button
                  type="button"
                  onClick={() => { onChange(valor); setAbierto(false) }}
                  style={{
                    width: '100%',
                    background: seleccionado ? 'var(--accent-soft)' : 'transparent',
                    border: 'none',
                    padding: '10px 12px',
                    fontSize: 14,
                    fontFamily: 'var(--font-body)',
                    color: texto,
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={e => { if (!seleccionado) e.currentTarget.style.background = 'var(--accent-soft)' }}
                  onMouseLeave={e => { if (!seleccionado) e.currentTarget.style.background = 'transparent' }}
                >
                  {etiqueta}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}