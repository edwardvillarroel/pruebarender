import { supabase, supabaseDisponible } from './supabase.js'
import { api } from './api.js'

const COLUMNAS_PRODUCTO_PUBLICO = [
  'id',
  'categoria_id',
  'nombre',
  'descripcion',
  'precio',
  'stock',
  'imagen',
  'imagen_url',
  'activo',
  'creado_en',
  'specs',
  'descuento',
  'badge',
  'precio_original',
  'rating',
  'resenas_count',
  'material',
  'tamano',
  'color',
  'nuevo_lanzamiento',
  'stock_minimo',
  'imagen_content_type',
  'imagen_thumb_content_type',
].join(',')

function normalizarSpecs(valor) {
  if (Array.isArray(valor)) return valor
  if (typeof valor !== 'string' || !valor.trim()) return null
  try {
    const parsed = JSON.parse(valor)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

function urlImagenApi(id, thumb = false) {
  if (!id) return null
  return thumb ? `/api/productos/${id}/thumb` : `/api/productos/${id}/imagen`
}

function urlImagenColorApi(colorId, thumb = false) {
  if (!colorId) return null
  return thumb ? `/api/productos/colores/${colorId}/thumb` : `/api/productos/colores/${colorId}/imagen`
}

export function normalizarProductoPublico(p, fallbackColor = null) {
  const id = String(p.id)
  const imagenUrl = p.imagen_url || null
  const fallbackImagen = fallbackColor
    ? urlImagenColorApi(fallbackColor.id, false)
    : null
  const fallbackThumb = fallbackColor
    ? urlImagenColorApi(fallbackColor.id, true)
    : null
  const tieneImagen = Boolean(imagenUrl || p.imagen || p.imagen_content_type)
  const tieneThumb = Boolean(imagenUrl || p.imagen_thumb_content_type || p.imagen || p.imagen_content_type)

  return {
    id,
    nombre: p.nombre,
    descripcion: p.descripcion ?? null,
    precio: Number(p.precio),
    stock: Number(p.stock ?? 0),
    imagen: imagenUrl || (tieneImagen ? urlImagenApi(id, false) : null) || fallbackImagen,
    imagen_url: imagenUrl,
    imagen_thumb: imagenUrl || (tieneThumb ? urlImagenApi(id, true) : null) || fallbackThumb,
    activo: p.activo !== false,
    categoria_id: String(p.categoria_id),
    creado_en: p.creado_en ?? null,
    specs: normalizarSpecs(p.specs),
    descuento: p.descuento ?? null,
    badge: p.badge ?? null,
    precio_original: p.precio_original != null ? Number(p.precio_original) : null,
    rating: p.rating != null ? Number(p.rating) : null,
    resenas_count: Number(p.resenas_count ?? 0),
    material: p.material ?? null,
    tamano: p.tamano ?? null,
    color: p.color ?? null,
    nuevo_lanzamiento: Boolean(p.nuevo_lanzamiento),
    stock_minimo: p.stock_minimo != null ? Number(p.stock_minimo) : null,
  }
}

export function normalizarCategoriaPublica(c) {
  return {
    id: String(c.id),
    nombre: c.nombre,
    descripcion: c.descripcion ?? null,
    imagen_url: c.imagen_url || null,
  }
}

async function obtenerFallbackColores(productos) {
  const faltantes = productos
    .filter((p) => !p.imagen_url && !p.imagen && !p.imagen_content_type && !p.imagen_thumb_content_type)
    .map((p) => p.id)
  if (!faltantes.length) return new Map()

  const { data, error } = await supabase
    .from('producto_colores')
    .select('id, producto_id, orden, imagen_content_type, imagen_thumb_content_type')
    .in('producto_id', faltantes)
    .order('orden', { ascending: true })

  if (error) {
    console.warn('No se pudo cargar fallback de colores del catálogo:', error.message)
    return new Map()
  }

  const mapa = new Map()
  for (const color of data || []) {
    const productoId = String(color.producto_id)
    const tieneImagen = Boolean(color.imagen_content_type || color.imagen_thumb_content_type)
    if (!tieneImagen || mapa.has(productoId)) continue
    mapa.set(productoId, color)
  }
  return mapa
}

async function listarProductosDesdeSupabase() {
  const { data, error } = await supabase
    .from('productos')
    .select(COLUMNAS_PRODUCTO_PUBLICO)
    .eq('activo', true)
    .order('creado_en', { ascending: false })

  if (error) throw new Error(error.message || 'No se pudo cargar el catálogo')
  const productos = data || []
  const fallbackColores = await obtenerFallbackColores(productos)
  return productos.map((p) => normalizarProductoPublico(p, fallbackColores.get(String(p.id)) || null))
}

async function listarCategoriasDesdeSupabase() {
  const { data, error } = await supabase
    .from('categorias')
    .select('id, nombre, descripcion, imagen_url')
    .order('nombre', { ascending: true })

  if (error) throw new Error(error.message || 'No se pudieron cargar las categorías')
  return (data || []).map(normalizarCategoriaPublica)
}

async function listarProductosDesdeApi() {
  const res = await api.get('/productos')
  return (res.productos ?? []).map(normalizarProductoPublico)
}

async function listarCategoriasDesdeApi() {
  const res = await api.get('/categorias')
  return (res.categorias ?? []).map(normalizarCategoriaPublica)
}

export async function listarProductosPublicos() {
  if (supabaseDisponible) return listarProductosDesdeSupabase()
  return listarProductosDesdeApi()
}

export async function listarCategoriasPublicas() {
  if (supabaseDisponible) return listarCategoriasDesdeSupabase()
  return listarCategoriasDesdeApi()
}
