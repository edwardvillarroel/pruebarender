import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../context/ThemeContext.jsx'
import { ChevronDown } from 'lucide-react'

export default function SelectOpciones({
  id,
  options,
  value,
  onChange,
  placeholder = 'Selecciona una opción',
  disabled = false,
  onAbierto,
}) {
  const { theme } = useTheme()
  const [abierto, setAbierto] = useState(false)
  const [hoverIdx, setHoverIdx] = useState(-1)
  const contRef = useRef(null)

  function cerrar() {
    setAbierto(false)
    setHoverIdx(-1)
  }

  useEffect(() => {
    function clickFuera(e) {
      if (contRef.current && !contRef.current.contains(e.target)) cerrar()
    }
    function tecla(e) {
      if (e.key === 'Escape') cerrar()
    }
    document.addEventListener('mousedown', clickFuera)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', clickFuera)
      document.removeEventListener('keydown', tecla)
    }
  }, [])

  useEffect(() => {
    if (disabled) cerrar()
  }, [disabled])

  const esOscuro = theme === 'dark'
  const fondo = esOscuro ? 'var(--surface)' : '#ffff'
  const texto = esOscuro ? 'var(--text)' : 'var(--surface)'
  const lista = options || []
  const valores = lista.map(o => (typeof o === 'string' ? o : o.value))
  const sinSeleccion = value == null || !valores.includes(value)
  const opSeleccionada = lista.find(o => (typeof o === 'string' ? o : o.value) === value)
  const etiquetaSeleccion = opSeleccionada
    ? (typeof opSeleccionada === 'string' ? opSeleccionada : opSeleccionada.label)
    : ''

  function toggle() {
    const nuevo = !abierto
    setAbierto(nuevo)
    setHoverIdx(-1)
    if (nuevo) onAbierto?.()
  }

  return (
    <div ref={contRef} style={{ position: 'relative' }}>
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={toggle}
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
            maxHeight: 115,
            overflowY: 'auto',
          }}
        >
          {lista.map((op, idx) => {
            const valor = typeof op === 'string' ? op : op.value
            const etiqueta = typeof op === 'string' ? op : op.label
            const seleccionado = valor === value
            const sobre = idx === hoverIdx
            return (
              <li
                key={valor}
                role="option"
                aria-selected={seleccionado}
                onMouseEnter={() => setHoverIdx(idx)}
                onMouseLeave={() => setHoverIdx(-1)}
              >
                <button
                  type="button"
                  onClick={() => { onChange(valor); cerrar() }}
                  style={{
                    width: '100%',
                    background: seleccionado ? 'var(--accent-soft)' : sobre ? 'var(--accent-soft)' : 'transparent',
                    border: 'none',
                    padding: '10px 12px',
                    fontSize: 14,
                    fontFamily: 'var(--font-body)',
                    color: texto,
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
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
