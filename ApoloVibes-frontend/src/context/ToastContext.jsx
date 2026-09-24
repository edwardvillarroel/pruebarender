import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'

const ToastContext = createContext(null)

const DURACION_VISIBLE = 2600

function ToastItem({ toast, onQuitar }) {
  const [saliendo, setSaliendo] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setSaliendo(true), DURACION_VISIBLE)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div
      className={`toast toast-${toast.tipo}${saliendo ? ' toast-salida' : ''}`}
      role="status"
      onAnimationEnd={() => saliendo && onQuitar(toast.id)}
    >
      {toast.tipo === 'exito' && <CheckCircle2 size={18} className="toast-icono" />}
      <span className="toast-mensaje">{toast.mensaje}</span>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const contador = useRef(0)

  const quitar = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const mostrar = useCallback((mensaje, tipo = 'exito') => {
    const id = ++contador.current
    setToasts(prev => [...prev, { id, mensaje, tipo }])
  }, [])

  return (
    <ToastContext.Provider value={mostrar}>
      {children}
      <div className="toast-contenedor" aria-live="polite">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onQuitar={quitar} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast debe usarse dentro de <ToastProvider>')
  return ctx
}