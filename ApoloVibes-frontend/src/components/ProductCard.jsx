import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useCart } from '../context/CartContext.jsx'
import { Star, ImageOff } from 'lucide-react'
import { IconShoppingCartPlus } from '@tabler/icons-react'
import { useState } from 'react'

const ACENTOS = ['#FA7F19', '#F6D976', '#E8863E']
const COLOR_NUEVO = '#2fa018'
const COLOR_DESCUENTO = '#FA7F19'
const COLOR_SIN_STOCK = '#e71414'
const COLOR_BUTTON = '#FA7F19'

export default function ProductCard({ producto, index = 0 }) {
  const { agregarProducto } = useCart()
  const acento = ACENTOS[index % ACENTOS.length]

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 16,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 4px 12px rgba(253, 137, 3, 0.86)',
        transition: 'transform .2s, box-shadow .2s'
      }}
    >
      <Link to={`/producto/${producto.id}`} style={{ position: 'relative', display: 'block' }}>
        <div
          style={{
            position: 'relative',
            width: '100%',
            aspectRatio: '1 / 1',
            background: producto.imagen ? '#FFFFFF' : 'var(--surface-2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {producto.imagen ? (
            <img
              src={producto.imagen}
              alt={producto.nombre}
              style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div
              style={{
                width: 90,
                height: 90,
                borderRadius: 12,
                background: 'var(--surface-2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ImageOff size={28} color="var(--text-dim)" strokeWidth={1.5} />
            </div>
          )}

          {producto.sinStock ? (
            <span
              style={{
                position: 'absolute',
                top: 19,
                right: -40,
                width: 150,
                transform: 'rotate(45deg)',
                background: COLOR_SIN_STOCK,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 500,
                lineHeight: '1.4',
                padding: '5px 0',
                textAlign: 'center',
              }}
            >
              SIN STOCK
            </span>
          ) : producto.descuento ? (
            <span
              style={{
                position: 'absolute',
                top: 19,
                right: -40,
                width: 150,
                transform: 'rotate(45deg)',
                background: COLOR_DESCUENTO,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 500,
                lineHeight: '1.4',
                padding: '5px 0',
                textAlign: 'center',
              }}
            >
              -{producto.descuento}%
            </span>
          ) : producto.badge ? (
            <div
              style={{
                position: 'absolute',
                top: 19,
                right: -40,
                width: 150,
                transform: 'rotate(45deg)',
                background: COLOR_NUEVO,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 500,
                lineHeight: '1.4',
                padding: '5px 0',
                textAlign: 'center',
              }}
            >
              {producto.badge}
            </div>
          ) : null}
        </div>
      </Link>

      <div style={{ padding: '18px 16px', flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h4 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>{producto.nombre}</h4>
        {producto.rating && (
          <div style={{ display: 'flex', gap: 2 }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                size={14}
                fill={i < producto.rating ? acento : 'none'}
                color={i < producto.rating ? acento : 'var(--line)'}
              />
            ))}
          </div>
        )}

        <div
          style={{
            marginTop: 'auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
              ${producto.precio.toLocaleString('es-CL')}
            </span>
            {producto.precioOriginal && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  color: 'var(--text-dim)',
                  textDecoration: 'line-through',
                }}
              >
                ${producto.precioOriginal.toLocaleString('es-CL')}
              </span>
            )}
          </div>

          <button
            onClick={() => agregarProducto(producto)}
            disabled={producto.sinStock}
            aria-label="Agregar al carrito"
            style={{
              background: producto.sinStock ? 'var(--surface-2)' : COLOR_BUTTON,
              color: producto.sinStock ? 'var(--text-dim)' : '#0B0D10',
              border: 'none',
              borderRadius: 999,
              width: 40,
              height: 40,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: producto.sinStock ? 'not-allowed' : 'pointer',
              transition: 'opacity .2s',
              flexShrink: 0,
              position: 'relative',
            }}
            onMouseEnter={(e) => !producto.sinStock && (e.currentTarget.style.opacity = '.85')}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
          >
            <img
              src={mediaPath('cart.png')}
              alt=""
              style={{
                width: 25, height: 25, filter: 'brightness(0) invert(1)',
                opacity: producto.sinStock ? 0.5 : 1,
              }}
            />
          </button>
        </div>
      </div>
    </div>
  )
}