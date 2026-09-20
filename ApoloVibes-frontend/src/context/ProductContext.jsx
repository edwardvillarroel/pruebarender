import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { productoApi } from '../services/products.js'

const ProductContext = createContext(null)

export function ProductProvider({ children }) {
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const primeraCarga = useRef(true)

  async function cargar(silencioso = false) {
    if (!silencioso) setCargando(true)
    setError(null)
    try {
      const [resProductos, resCategorias] = await Promise.all([
        productoApi.obtener(),
        productoApi.listarCategorias(),
      ])
      setProductos(resProductos.productos ?? [])
      setCategorias(resCategorias.categorias ?? [])
    } catch (err) {
      console.error('Error al cargar catálogo:', err)
      setError(err.message)
    } finally {
      setCargando(false)
      primeraCarga.current = false
    }
  }

  /** Actualiza un producto en el estado local sin re-fetch al API */
  function actualizarLocal(datos) {
    setProductos(prev =>
      prev.map(p => p.id === datos.id ? { ...p, ...datos } : p)
    )
  }

  /** Elimina un producto del estado local sin re-fetch al API */
  function eliminarLocal(id) {
    setProductos(prev => prev.filter(p => p.id !== id))
  }

  useEffect(() => {
    cargar()
  }, [])

  const categoriasConConteo = useMemo(
    () =>
      categorias.map(cat => ({
        ...cat,
        cantidad: productos.filter(p => p.categoria_id === cat.id).length,
      })),
    [categorias, productos]
  )

  const productosConEstado = useMemo(
    () =>
      productos.map(p => ({
        ...p,
        sinStock: Number(p.stock) <= 0,
      })),
    [productos]
  )

  return (
    <ProductContext.Provider
      value={{
        productos: productosConEstado,
        categorias: categoriasConConteo,
        cargando,
        error,
        recargar: () => cargar(true),
        actualizarLocal,
        eliminarLocal,
      }}
    >
      {children}
    </ProductContext.Provider>
  )
}

export function useProductos() {
  const ctx = useContext(ProductContext)
  if (!ctx) throw new Error('useProductos debe usarse dentro de <ProductProvider>')
  return ctx
}
