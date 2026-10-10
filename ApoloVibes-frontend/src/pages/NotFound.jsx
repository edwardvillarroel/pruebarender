import { useNavigate } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'


const FONDO_404 = {
  backgroundImage: `url(${mediaPath('404.png')})`,
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'center center',
  backgroundSize: 'contain',
}
const COLOR_FONDO_404 = '#faf9f7'
const MASCARA_LATERAL =
  'linear-gradient(to right, transparent 0, #000 6%, #000 94%, transparent 100%)'

function ContenidoNotFound() {
  const navegar = useNavigate()

  return (
    <div
      style={{
        width: '100%',
        flex: 1,
        marginBottom: '-60px',
        minHeight: '58vh',
        backgroundColor: COLOR_FONDO_404,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
    
      <div style={{ position: 'relative', width: 'min(100%, 87vh)', aspectRatio: '3 / 2' }}>
        <img
          src={mediaPath('404.png')}
          alt="Error 404: esta página no existe"
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            WebkitMaskImage: MASCARA_LATERAL,
            maskImage: MASCARA_LATERAL,
          }}
        />
        <button
          type="button"
          onClick={() => navegar('/', { replace: true })}
          style={{
            position: 'absolute',
            left: '79%',
            top: '76%',
            transform: 'translate(-50%, -50%)',
            background: 'var(--accent)',
            color: 'var(--text)',
            border: 'none',
            borderRadius: 10,
            padding: '10px 22px',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'opacity .2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85' }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
        >
          Volver al inicio
        </button>
      </div>
    </div>
  )
}
// Variante de pantalla completa: se usa como fallback de ErrorBoundary.
function PantallaCompletaNotFound() {
  return (
    <div
      style={{
        ...FONDO_404,
        backgroundColor: COLOR_FONDO_404,
        width: '100%',
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '40px 20px',
      }}
    >
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        
        <button
          type="button"
          onClick={() => window.location.assign(import.meta.env.BASE_URL)}
          style={{
            background: 'var(--accent)',
            color: '#0B0D10',
            border: 'none',
            borderRadius: 10,
            padding: '10px 22px',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'opacity .2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85' }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
        >
          Volver al inicio
        </button>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{
            background: 'none',
            color: '#5A6B7D',
            border: '1px solid #5A6B7D',
            borderRadius: 10,
            padding: '10px 22px',
            fontSize: 13,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'border-color .2s, color .2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)'
            e.currentTarget.style.color = 'var(--accent)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#5A6B7D'
            e.currentTarget.style.color = '#5A6B7D'
          }}
        >
          Recargar la página
        </button>
      </div>
    </div>
  )
}

export default function NotFound({ completo = false }) {
  return completo ? <PantallaCompletaNotFound /> : <ContenidoNotFound />
}
