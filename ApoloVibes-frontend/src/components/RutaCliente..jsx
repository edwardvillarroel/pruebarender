import { useEffect } from 'react'
import { LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useCart } from '../context/CartContext.jsx'

export default function RutaCliente({ children }) {
    const { isLoggedIn } = useAuth()
    const { abrirLogin } = useCart()

    useEffect(() => {
        if (!isLoggedIn) abrirLogin()
    }, [])

    if (isLoggedIn) return children

    return (
        <section className="wrap" style={{ padding: '100px 20px', textAlign: 'center', maxWidth: 480, margin: '0 auto' }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 10, color: 'var(--surface)' }}>
                Inicia sesión para cotizar
            </h1>
            <p style={{ color: 'var(--text-dim)', marginBottom: 20, lineHeight: 1.6 }}>
                Necesitas una cuenta para enviar una solicitud de cotización.
            </p>
            <button
                className="btn btn-primary"
                onClick={abrirLogin}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}
            >
                <LogIn size={16} /> Iniciar sesión
            </button>
        </section>
    )
}