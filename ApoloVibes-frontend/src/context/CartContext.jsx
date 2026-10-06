import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { carritoApi } from '../services/cart.js'
import { imagenDeColor } from '../services/products.js'
import { useAuth } from './AuthContext.jsx'
import { useProductos } from './ProductContext.jsx'
import { useToast } from './ToastContext.jsx'

const CartContext = createContext(null)

function enrichItem(linea, productos) {
  const prod = productos.find(p => p.id === linea.producto_id)
  const imagen = linea.imagen
    ?? imagenDeColor(linea.producto_id, linea.color)
    ?? prod?.imagen
    ?? null
  return {
    id: linea.producto_id,
    itemId: linea.id,
    productoId: linea.producto_id,
    cantidad: linea.cantidad,
    color: linea.color ?? null,
    nombre: prod?.nombre ?? 'Producto',
    precio: prod?.precio ?? 0,
    precio_original: prod?.precio_original ?? null,
    imagen,
  }
}

function enrichCart(carrito, productos) {
  return (carrito?.items ?? []).map(linea => enrichItem(linea, productos))
}

export function CartProvider({ children }) {
  const { isLoggedIn } = useAuth()
  const { productos } = useProductos()
  const mostrarToast = useToast()
  const [items, setItems] = useState([])
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const [solicitarLogin, setSolicitarLogin] = useState(false)
  const carritoRef = useRef(null)
  const itemsRef = useRef([])
  const seqRef = useRef(0)

  const syncItems = useCallback((carrito) => {
    carritoRef.current = carrito
    actualizarItems(enrichCart(carrito, productos))
  }, [productos])

  useEffect(() => {
    if (isLoggedIn) {
      cargarCarrito()
    } else {
      syncItems(null)
      setError(null)
    }
  }, [isLoggedIn])


  useEffect(() => {
    if (carritoRef.current) {
      syncItems(carritoRef.current)
    }
  }, [productos])

  async function cargarCarrito() {
    if (!isLoggedIn) return
    setCargando(true)
    try {
      const { carrito } = await carritoApi.obtener()
      syncItems(carrito)
    } catch (err) {
      console.error('Error al cargar carrito:', err)
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  function actualizarItems(actualizar) {
    const next = typeof actualizar === 'function' ? actualizar(itemsRef.current) : actualizar
    itemsRef.current = next
    setItems(next)
  }


function mismaLinea(a, producto, color) {
  return a.id === producto.id && (a.color ?? null) === (color ?? null)
}

function optimistaAgregar(producto, cantidad = 1) {
  const color = producto.color ?? null
  actualizarItems(prev => {
    const existente = prev.find(i => mismaLinea(i, producto, color))
    if (existente) {
      return prev.map(i => i === existente ? { ...i, cantidad: i.cantidad + cantidad } : i)
    }
    return [...prev, {
      id: producto.id,
      itemId: `temp-${producto.id}-${color || 'sin-color'}`,
      productoId: producto.id,
      cantidad,
      color,
      nombre: producto.nombre,
      precio: producto.precio ?? 0,
      precio_original: producto.precio_original ?? null,
      imagen: producto.imagen ?? null,
    }]
  })
}

function reversarAgregar(producto) {
  const color = producto.color ?? null
  actualizarItems(prev => {
    const idx = prev.findIndex(i => mismaLinea(i, producto, color))
    if (idx === -1) return prev
    const item = prev[idx]
    if (item.cantidad > 1) {
      return prev.map(i => i === item ? { ...i, cantidad: i.cantidad - 1 } : i)
    }
    return prev.filter(i => i !== item)
  })
}

  function optimistaQuitar(itemId) {
    actualizarItems(prev => prev.filter(i => i.itemId !== itemId && i.id !== itemId))
  }

  function optimistaCantidad(itemId, cantidad) {
    actualizarItems(prev => prev.map(i => (i.itemId === itemId || i.id === itemId) ? { ...i, cantidad } : i))
  }


  function fireAndReconcile(fn) {
    const op = ++seqRef.current
    fn()
      .then(({ carrito }) => {
        if (op === seqRef.current) syncItems(carrito)
      })
      .catch(err => {
        if (op !== seqRef.current) return
        setError(err.message)
        cargarCarrito()
      })
  }

  function esTemp(itemId) {
    return String(itemId).startsWith('temp-')
  }

  function abrirLogin() {
    setError('Inicia sesión para usar el carrito')
    setSolicitarLogin(true)
  }

  function cerrarLogin() {
    setSolicitarLogin(false)
  }

  async function agregarProducto(producto, cantidad = 1) {
    if (!isLoggedIn){
      abrirLogin() 
      return false
    }
    setError(null)
    const color = producto.color ?? null
    //optimistaAgregar(producto, cantidad)
    const op = ++seqRef.current
    try {
      const { carrito } = await carritoApi.agregarProducto(producto.id, cantidad, color)
      if (op === seqRef.current) syncItems(carrito)
        mostrarToast('Producto agregado exitosamente')
        return true
    } catch (err) {
      setError(err.message)
      return false
    }
  }

  function quitarItem(itemId) {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    optimistaQuitar(itemId)
    if (esTemp(itemId)) return
    fireAndReconcile(() => carritoApi.eliminarItem(itemId))
  }

  function actualizarCantidadItem(itemId, cantidad) {
    if (!isLoggedIn) return abrirLogin()
    if (esTemp(itemId)) {
      optimistaCantidad(itemId, cantidad)
      return
    }
    setError(null)
    optimistaCantidad(itemId, cantidad)
    fireAndReconcile(() => carritoApi.actualizarCantidad(itemId, cantidad))
  }

  function vaciarCarrito() {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    actualizarItems([])
    fireAndReconcile(() => carritoApi.vaciar())
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
      value={{
        items, total, cantidadTotal, cargando, error,
        requiereLogin: !isLoggedIn, solicitarLogin,
        cargarCarrito, abrirLogin, cerrarLogin,
        agregarProducto, quitarItem, actualizarCantidadItem, vaciarCarrito,
      }}
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