import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { productoApi } from '../services/products.js'

const ProductContext = createContext(null)

export function ProductProvider({ children }) {
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)

  async function cargar() {
    setCargando(true)
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
    }
  }

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        recargar: cargar,
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