import { Link } from 'react-router-dom'
import { mediaPath } from '../utils/media.js'
import { useCart } from '../context/CartContext.jsx'
import { useProductos } from '../context/ProductContext.jsx'
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
  const { categorias } = useProductos()
  const acento = ACENTOS[index % ACENTOS.length]
  const categoria = categorias.find(c => c.id === producto.categoria_id)
  const imagenTarjeta = producto.imagen_thumb || producto.imagen

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border-card)',
        borderRadius: 16,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 2px 4px rgba(253, 137, 3, 0.86)',
        transition: 'transform .2s, box-shadow .2s'
      }}
    >
      <Link to={`/producto/${producto.id}`} style={{ position: 'relative', display: 'block' }}>
        <div
          style={{
            position: 'relative',
            width: '100%',
            aspectRatio: '1 / 1',
            background: imagenTarjeta ? '#FFFFFF' : 'var(--surface-2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {imagenTarjeta ? (
            <img
              src={imagenTarjeta}
              alt={producto.nombre}
              loading="lazy"
              decoding="async"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
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

          {producto.descuento ? (
            <span
              style={{
                position: 'absolute',
                top: 10,
                left: 10,
                background: COLOR_DESCUENTO,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 700,
                padding: '4px 12px',
                borderRadius: 20,
                zIndex: 2,
              }}
            >
              -{producto.descuento}% OFF
            </span>
          ) : producto.sinStock ? (
            <span
              style={{
                position: 'absolute',
                top: 10,
                left: 10,
                background: COLOR_SIN_STOCK,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 700,
                padding: '4px 12px',
                borderRadius: 20,
                zIndex: 2,
              }}
            >
              AGOTADO
            </span>
          ) : producto.badge ? (
            <span
              style={{
                position: 'absolute',
                top: 10,
                left: 10,
                background: COLOR_NUEVO,
                color: '#FFFFFF',
                fontSize: 12,
                fontWeight: 700,
                padding: '4px 12px',
                borderRadius: 20,
                zIndex: 2,
              }}
            >
              {producto.badge}
            </span>
          ) : null}

          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 0,
              height: 55,
              background: 'linear-gradient(to bottom, rgba(0,0,0,0), var(--surface))',
              pointerEvents: 'none',
              zIndex: 1,
            }}
          />
        </div>
      </Link>

      <div style={{ padding: '10px 16px', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', flex: 1, minWidth: 0 }}>{producto.nombre}</h4>
          {categoria && (
            <span
              style={{
                display: 'inline-block',
                flexShrink: 0,
                maxWidth: '100%',
                background: 'transparent',
                border: '1px solid var(--accent)',
                color: 'var(--accent)',
                fontSize: 11,
                fontWeight: 600,
                padding: '3px 10px',
                borderRadius: 999,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {categoria.nombre}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
            ${producto.precio.toLocaleString('es-CL')}
          </span>
          {producto.precio_original && (
            <span
              style={{
                fontSize: 12,
                color: 'var(--text-dim)',
                textDecoration: 'line-through',
              }}
            >
              ${producto.precio_original.toLocaleString('es-CL')}
            </span>
          )}
          {producto.sinStock ? (
            <span
              style={{
                display: 'inline-block',
                background: 'var(--surface-3)',
                color: 'var(--text-dim)',
                fontSize: 11,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 999,
                width: 'fit-content',
              }}
            >
              AGOTADO
            </span>
          ) : null}
        </div>
        <p style={{ color: 'var(--text-dim)', fontWeight: 600, fontSize: 10, marginTop: -10 }}>IVA incluido</p>

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

        <button
          onClick={() => agregarProducto(producto)}
          disabled={producto.sinStock}
          aria-label="Agregar al carrito"
          style={{
            marginTop: 'auto',
            background: producto.sinStock ? 'var(--surface-3)' : COLOR_BUTTON,
            color: producto.sinStock ? 'var(--text-dim)' : 'var(--text)',
            border: 'none',
            borderRadius: 12,
            width: '100%',
            height: 40,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            cursor: producto.sinStock ? 'not-allowed' : 'pointer',
            transition: 'opacity .2s',
          }}
          onMouseEnter={(e) => !producto.sinStock && (e.currentTarget.style.opacity = '.85')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
        > Agregar
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
  )
}