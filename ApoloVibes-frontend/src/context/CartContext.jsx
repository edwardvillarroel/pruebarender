import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { carritoApi } from '../services/cart.js'
import { useAuth } from './AuthContext.jsx'
import { useProductos } from './ProductContext.jsx'
import { useToast } from './ToastContext.jsx'

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
      syncItems(carritoRef.current)
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

  function actualizarItems(actualizar) {
    const next = typeof actualizar === 'function' ? actualizar(itemsRef.current) : actualizar
    itemsRef.current = next
    setItems(next)
  }

  function optimistaAgregar(producto, cantidad = 1) {
    actualizarItems(prev => {
      const existente = prev.find(i => i.id === producto.id)
      if (existente) {
        return prev.map(i => i.id === producto.id ? { ...i, cantidad: i.cantidad + cantidad } : i)
      }
      return [...prev, {
        id: producto.id,
        itemId: `temp-${producto.id}`,
        productoId: producto.id,
        cantidad,
        nombre: producto.nombre,
        precio: producto.precio ?? 0,
        precio_original: producto.precio_original ?? null,
        imagen: producto.imagen ?? null,
      }]
    })
  }

  function reversarAgregar(producto) {
    actualizarItems(prev => {
      const idx = prev.findIndex(i => i.id === producto.id)
      if (idx === -1) return prev
      const item = prev[idx]
      if (item.cantidad > 1) {
        return prev.map(i => i.id === producto.id ? { ...i, cantidad: i.cantidad - 1 } : i)
      }
      return prev.filter(i => i.id !== producto.id)
    })
  }

  function optimistaQuitar(itemId) {
    actualizarItems(prev => prev.filter(i => i.itemId !== itemId && i.id !== itemId))
  }

  function optimistaCantidad(itemId, cantidad) {
    actualizarItems(prev => prev.map(i => (i.itemId === itemId || i.id === itemId) ? { ...i, cantidad } : i))
  }

  // Ejecuta la petición y reconcilia con el servidor solo si sigue siendo la
  // mutación más reciente; así las respuestas encoladas/desordenadas no pisan
  // el estado ya optimista de una operación más nueva.
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

  function agregarProducto(producto, cantidad = 1) {
    if (!isLoggedIn) return abrirLogin()
    setError(null)
    optimistaAgregar(producto, cantidad)

    const op = ++seqRef.current
    carritoApi.agregarProducto(producto.id, cantidad)
      .then(({ carrito }) => {
        if (op !== seqRef.current) return
        // Si el producto se eliminó de la vista antes de que respondiera el
        // servidor, borrar la línea recién creada para no dejarla huérfana.
        const sigueEnVista = itemsRef.current.some(i => i.id === producto.id)
        syncItems(carrito)
        mostrarToast('Producto agregado exitosamente')
        if (!sigueEnVista) {
          const linea = carrito?.items?.find(i => i.producto_id === producto.id)
          if (linea) carritoApi.eliminarItem(linea.id).catch(() => {})
        }
      })
      .catch(err => {
        if (op !== seqRef.current) return
        setError(err.message)
        reversarAgregar(producto)
      })
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