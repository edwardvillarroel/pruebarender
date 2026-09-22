import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'

export default function CompraExitosa() {
  return (
    <div className="wrap" style={{ paddingTop: '80px', paddingBottom: '80px', textAlign: 'center' }}>
      <CheckCircle2 size={72} strokeWidth={1.5} style={{ display: 'block', margin: '0 auto 20px', color: '#22c55e' }} />
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, margin: 0, color: 'var(--surface)' }}>
        ¡Compra realizada con éxito!
      </h1>
      <p style={{ color: 'var(--text-dim)', margin: '12px auto 24px', maxWidth: 420, lineHeight: 1.6 }}>
        Tu pedido fue registrado. Pronto estará en camino.
      </p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <Link to="/categorias" className="btn btn-primary">Seguir comprando</Link>
        <Link to="/" className="btn btn-ghost">Volver al inicio</Link>
      </div>
    </div>
  )
}