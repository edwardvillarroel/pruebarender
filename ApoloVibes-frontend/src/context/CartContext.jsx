import { createContext, useContext, useMemo, useState, useEffect } from 'react'

const CART_KEY = 'apolovibes_cart'

function loadCart() {
  try {
    const raw = localStorage.getItem(CART_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [items, setItems] = useState(loadCart)

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(items))
  }, [items])

  function agregarProducto(producto, cantidad = 1) {
    setItems(prev => {
      const existe = prev.find(i => i.id === producto.id)
      if (existe) {
        return prev.map(i =>
          i.id === producto.id ? { ...i, cantidad: i.cantidad + cantidad } : i
        )
      }
      return [...prev, { ...producto, cantidad }]
    })
  }

  function quitarProducto(id) {
    setItems(prev => prev.filter(i => i.id !== id))
  }

  function actualizarCantidad(id, cantidad) {
    setItems(prev =>
      prev.map(i => (i.id === id ? { ...i, cantidad: Math.max(1, cantidad) } : i))
    )
  }

  function vaciarCarrito() {
    setItems([])
  }

  const total = useMemo(
    () => items.reduce((acc, i) => acc + i.precio * i.cantidad, 0),
    [items]
  )

  const cantidadTotal = useMemo(
    () => items.reduce((acc, i) => acc + i.cantidad, 0),
    [items]
  )

  return (
    <CartContext.Provider
      value={{ items, agregarProducto, quitarProducto, actualizarCantidad, vaciarCarrito, total, cantidadTotal }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart debe usarse dentro de <CartProvider>')
  return ctx
}
