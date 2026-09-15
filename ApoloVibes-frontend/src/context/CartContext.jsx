import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { carritoApi } from '../services/cart.js'
import { useAuth } from './AuthContext.jsx'
import { useProductos } from './ProductContext.jsx'

const CartContext = createContext(null)

function enrichItem(linea, productos) {
  const prod = productos.find(p => p.id === linea.producto_id)
  return {
    id: linea.producto_id,
    itemId: linea.id,
    productoId: linea.producto_id,
    cantidad: linea.cantidad,
    nombre: prod?.nombre ?? 'Producto',
    precio: prod?.precio ?? 0,
    precio_original: prod?.precio_original ?? null,
    imagen: prod?.imagen ?? null,
  }
}

function enrichCart(carrito, productos) {
  return (carrito?.items ?? []).map(linea => enrichItem(linea, productos))
}

export function CartProvider({ children }) {
  const { isLoggedIn } = useAuth()
  const { productos } = useProductos()
  const [items, setItems] = useState([])
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const [solicitarLogin, setSolicitarLogin] = useState(false)
  const carritoRef = useRef(null)

  const syncItems = useCallback((carrito) => {
    carritoRef.current = carrito
    setItems(enrichCart(carrito, productos))
  }, [productos])

  // El carrito vive por usuario real (JWT). Al entrar/salir de sesión se
  // (re)carga desde la base; al cerrar sesión se vacía la vista local.
  useEffect(() => {
    if (isLoggedIn) {
      cargarCarrito()
    } else {
      syncItems(null)
      setError(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn])

  // Cuando llegan los productos del catálogo (o cambian) se re-enriquecen las
  // líneas del carrito ya cargadas para mostrar nombre/precio correctos.
  useEffect(() => {
    if (carritoRef.current) {
      setItems(enrichCart(carritoRef.current, productos))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  function abrirLogin() {
    setError('Inicia sesión para usar el carrito')
    setSolicitarLogin(true)
  }

  function cerrarLogin() {
    setSolicitarLogin(false)
  }

  async function agregarProducto(producto, cantidad = 1) {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    try {
      const { carrito } = await carritoApi.agregarProducto(producto.id, cantidad)
      syncItems(carrito)
    } catch (err) {
      setError(err.message)
    }
  }

  async function quitarItem(itemId) {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    try {
      const { carrito } = await carritoApi.eliminarItem(itemId)
      syncItems(carrito)
    } catch (err) {
      setError(err.message)
    }
  }

  async function actualizarCantidadItem(itemId, cantidad) {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    try {
      const { carrito } = await carritoApi.actualizarCantidad(itemId, cantidad)
      syncItems(carrito)
    } catch (err) {
      setError(err.message)
    }
  }

  async function vaciarCarrito() {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    try {
      const { carrito } = await carritoApi.vaciar()
      syncItems(carrito)
    } catch (err) {
      setError(err.message)
    }
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