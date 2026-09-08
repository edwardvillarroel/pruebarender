import { Sparkles, Loader2, CheckCircle2, XCircle } from 'lucide-react'

const STATUS_CONFIG = {
  idle: { icon: Sparkles, color: 'var(--text-dim)', bgColor: 'var(--surface-2)' },
  uploading: { icon: Loader2, color: '#E8863E', bgColor: 'var(--surface)' },
  processing: { icon: Loader2, color: '#E8863E', bgColor: 'var(--surface)' },
  completed: { icon: CheckCircle2, color: '#22c55e', bgColor: 'var(--surface)' },
  failed: { icon: XCircle, color: '#ef4444', bgColor: 'var(--surface)' },
}

const STEPS = [
  { key: 'uploading', label: 'Subir imagen' },
  { key: 'processing', label: 'Generar modelo 3D' },
  { key: 'completed', label: 'Modelo listo' },
]

export default function GenerationProgress({ status = 'idle', percent = 0, message = '' }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.idle
  const Icon = config.icon
  const isSpinning = status === 'uploading' || status === 'processing'

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      padding: 20,
      marginTop: 16,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: config.bgColor,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon
            size={20}
            color={config.color}
            style={isSpinning ? { animation: 'spin 1s linear infinite' } : {}}
          />
        </div>
        <div>
          <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
            Generando modelo 3D
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>
            {message || 'Esperando...'}
          </p>
        </div>
        <span style={{
          marginLeft: 'auto',
          fontFamily: 'var(--font-mono)',
          fontSize: 13,
          fontWeight: 600,
          color: config.color,
        }}>
          {Math.round(percent)}%
        </span>
      </div>

      {/* Progress bar */}
      <div style={{
        width: '100%',
        height: 6,
        borderRadius: 3,
        background: 'var(--surface-2)',
        overflow: 'hidden',
        marginBottom: 16,
      }}>
        <div style={{
          width: `${percent}%`,
          height: '100%',
          borderRadius: 3,
          background: status === 'failed'
            ? '#ef4444'
            : status === 'completed'
              ? '#22c55e'
              : 'linear-gradient(90deg, #E8863E, #F6D976)',
          transition: 'width .4s ease',
        }} />
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', gap: 8 }}>
        {STEPS.map((step, i) => {
          const stepIndex = STEPS.findIndex(s => s.key === status)
          const isDone = i < stepIndex || status === 'completed'
          const isCurrent = step.key === status

          return (
            <div
              key={step.key}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
                color: isDone ? '#22c55e' : isCurrent ? config.color : 'var(--text-dim)',
                fontWeight: isCurrent ? 600 : 400,
              }}
            >
              <div style={{
                width: 6, height: 6, borderRadius: '50%',
                background: isDone ? '#22c55e' : isCurrent ? config.color : 'var(--line)',
                flexShrink: 0,
              }} />
              {step.label}
            </div>
          )
        })}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
