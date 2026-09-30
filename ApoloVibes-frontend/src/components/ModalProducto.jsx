import { useState, useLayoutEffect, useMemo, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../services/api.js'
import { productoApi } from '../services/products.js'
import SelectOpciones from './SelectOpciones.jsx'
import { Upload, Trash2 } from 'lucide-react'
import { mediaPath } from '../utils/media.js'


const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 9999, backdropFilter: 'blur(4px)', padding: 20,
}

const modalStyle = {
    background: 'var(--surface)', borderRadius: 20,
    width: '100%', maxWidth: 520, maxHeight: '90vh',
    boxShadow: '0 20px 60px rgba(0,0,0,.3)', position: 'relative',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
}

const inputStyle = {
    width: '100%', padding: '11px 14px', borderRadius: 10,
    border: '1px solid var(--line)', background: 'var(--bg)',
    color: 'var(--input-text)', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
}

const labelStyle = {
    fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 6,
}

const fieldGroup = {
    marginBottom: 16,
}

const grid2 = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }
const grid3 = { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, alignItems: 'start' }

const ALTO_CONTROL = 44
const ALTURA_MAX_DESC = 280
const LIMITE_DESCRIPCION = 20000

const MATERIALES = ['PLA+', 'PLA', 'ABS+']
const EXTENSIONES_RAW = ['raw', 'dng', 'nef', 'nrw', 'arw', 'srf', 'sr2', 'raf', 'rw2', 'orf', 'pef', 'srw', 'mrw', 'x3f', '3fr', 'iiq', 'kdc', 'dcr', 'erf', 'mos', 'cr2', 'cr3']
const ACEPTAR_IMAGENES = ['image/*', ...EXTENSIONES_RAW.map((ext) => `.${ext}`)].join(',')

function esRaw(nombreArchivo) {
    if (!nombreArchivo || !nombreArchivo.includes('.')) return false
    const extension = nombreArchivo.split('.').pop().toLowerCase()
    return EXTENSIONES_RAW.includes(extension)
}

const MENSAJE_ARCHIVO_INVALIDO = 'El archivo debe ser una imagen (JPG, PNG o WEBP) o un RAW de cámara (CR2, NEF, DNG).'

function esArchivoValido(archivo) {
    if (!archivo) return true
    return esRaw(archivo.name) || archivo.type.startsWith('image/')
}

function aplicarIva(neto) {
    if (neto <= 0) return neto
    return Math.ceil((neto * (100 + 19)) / 100)
}

function validarFormulario(form, esEdicion) {
    const nombre = form.nombre.trim()
    if (!nombre) return 'El nombre es obligatorio'
    if (nombre.length > 100) return 'El nombre es demasiado largo (máx. 100 caracteres)'

    if (!form.categoria_id) return 'Selecciona una categoria'

    const precio = Number(form.precio)
    if (!form.precio || Number.isNaN(precio) || precio <= 0) {
        return 'El precio debe ser un número mayor a 0'
    }

    if (form.descripcion) {
        const desc = form.descripcion.trim()
        if (desc.length > LIMITE_DESCRIPCION) return 'La descripción es muy larga (máx. 2000 caracteres)'
        if (/<script|javascript:|on\w+\s*=/i.test(desc)) {
            return 'La descripción contiene contenido no permitido'
        }
    }

    if (form.stock !== '' && form.stock !== undefined) {
        const stock = Number(form.stock)
        if (Number.isNaN(stock) || stock < 0 || !Number.isInteger(stock)) {
            return 'El stock debe ser un número entero igual o mayor a 0'
        }
    }

    if (form.descuento !== '' && form.descuento !== undefined && form.descuento !== null) {
        if (!/^\d{1,2}$/.test(String(form.descuento))) {
            return 'El descuyento debe tener máximo 2 cifras'
        }
        const descuento = Number(form.descuento)
        if (Number.isNaN(descuento) || descuento < 0 || descuento >= 100) {
            return 'El descuento debe estar entre 0 y 99'
        }
    }

    if (form.tamano && form.tamano.trim().length > 60) {
        return 'El tamaño es demasiado largo'
    }

    if (form.color) {
        const color = form.color.trim()
        if (color.length > 40) return 'El color es demasiado largo'
        if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s/]+$/.test(color)) {
            return 'El color solo puede contener letras y "/"'
        }
    }
    return null
}


export default function ModalProducto({ producto, categorias, onClose, onGuardado }) {
    const esEdicion = !!producto

    const [form, setForm] = useState({
        nombre: producto?.nombre || '',
        descripcion: producto?.descripcion || '',
        categoria_id: producto?.categoria_id || (categorias[0]?.id ?? ''),
        precio: producto?.precio_original ?? producto?.precio ?? '',
        stock: producto?.stock ?? '',
        material: producto?.material || '',
        tamano: producto?.tamano || '',
        color: producto?.color || '',
        descuento: producto?.descuento ?? '',
        nuevo_lanzamiento: producto?.nuevo_lanzamiento ?? false,
    })
    const [foto, setFoto] = useState(null)
    const [fotoPreview, setFotoPreview] = useState(null)
    const [error, setError] = useState('')
    const [cargando, setCargando] = useState(false)
    const [colores, setColores] = useState([])
    const [coloresPendientes, setColoresPendientes] = useState([])
    const [nuevoColor, setNuevoColor] = useState('')
    const [fotoColor, setFotoColor] = useState(null)
    const [subiendoColor, setSubiendoColor] = useState(false)
    const idCreadoRef = useRef(null)
    const resultadoGuardadoRef = useRef(null)
    const fotoSubidaRef = useRef(false)
    const coloresSubidosRef = useRef(0)
    const descripcionRef = useRef(null)
    const errorActual = useMemo(() => validarFormulario(form, esEdicion), [form, esEdicion])

    useLayoutEffect(() => {
        const el = descripcionRef.current
        if (!el) return
        el.style.height = 'auto'
        const alto = Math.min(el.scrollHeight, ALTURA_MAX_DESC)
        el.style.height = `${alto}px`
        el.style.overflowY = el.scrollHeight > ALTURA_MAX_DESC ? 'auto' : 'hidden'
    }, [form.descripcion])

    useEffect(() => {
        if (!esEdicion) return
        let vigente = true
        productoApi.listarColores(producto.id)
            .then(r => { if (vigente) setColores(r.colores || []) })
            .catch(() => { if (vigente) setColores([]) })
        return () => { vigente = false }
    }, [esEdicion, producto?.id])

    async function agregarColor(e) {
        e.preventDefault()
        const nombre = nuevoColor.trim()
        if (!nombre || !fotoColor) return
        setError('')

        const yaExiste = esEdicion
            ? colores.some(c => c.nombre.toLowerCase() === nombre.toLowerCase())
            : coloresPendientes.some(c => c.nombre.toLowerCase() === nombre.toLowerCase())

        if (yaExiste) {
            setError(`El color «${nombre}» ya está agregado`)
            return
        }

        if (!esEdicion) {
            setColoresPendientes(prev => [...prev, { nombre, archivo: fotoColor }])
            setNuevoColor('')
            setFotoColor(null)
            return
        }

        setSubiendoColor(true)
        try {
            const { color } = await productoApi.guardarColor(producto.id, nombre, fotoColor)
            setColores(prev => [...prev.filter(c => c.id !== color.id), color])
            setNuevoColor('')
            setFotoColor(null)
        } catch (err) {
            setError(err.message)
        } finally {
            setSubiendoColor(false)
        }
    }

    function quitarColorPendiente(nombre) {
        setColoresPendientes(prev => prev.filter(c => c.nombre !== nombre))
    }

    async function borrarColor(colorId) {
        setError('')
        const snapshot = colores
        setColores(prev => prev.filter(c => c.id !== colorId))
        try {
            await productoApi.eliminarColor(colorId)
        } catch (err) {
            setColores(snapshot)
            setError(err.message)
        }
    }

    useEffect(() => {
        if (foto && !esRaw(foto.name)) {
            const url = URL.createObjectURL(foto)
            setFotoPreview(url)
            return () => URL.revokeObjectURL(url)
        }
        setFotoPreview(null)
    }, [foto])

    const precioNeto = Number(form.precio) || 0
    const precioBase = esEdicion ? precioNeto : aplicarIva(precioNeto)
    const desc = Number(form.descuento) || 0
    const precioFinal = useMemo(() => {
        if (precioBase <= 0 || desc <= 0 || desc >= 100) return precioBase
        return Math.ceil((precioBase * (100 - desc)) / 100)
    }, [precioBase, desc])

    const precioOriginalPreview = useMemo(() => {
        if (precioBase <= 0 || desc <= 0 || desc >= 100) return null
        return precioBase
    }, [precioBase, desc])

    useLayoutEffect(() => {
        const scrollY = window.scrollY
        document.body.style.position = 'fixed'
        document.body.style.top = `-${scrollY}px`
        document.body.style.width = '100%'
        document.body.style.overflow = 'hidden'
        return () => {
            document.body.style.position = ''
            document.body.style.top = ''
            document.body.style.width = ''
            document.body.style.overflow = ''
            window.scrollTo(0, scrollY)
        }
    }, [])

    const set = (campo) => (e) => setForm(f => ({ ...f, [campo]: e.target.value }))

    const manejarDescuento = (e) => {
        let valor = e.target.value.replace(/\D/g, '')
        if (valor.length > 2) valor = valor.slice(0, 2)
        if (Number(valor) > 99) valor = '99'
        setForm(f => ({ ...f, descuento: valor }))
    }

    const manejarColor = (e) => {
        const valor = e.target.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s/]/g, '')
        setForm(f => ({ ...f, color: valor }))
    }

    const manejarNuevoColor = (e) => {
        let valor = e.target.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '')
        if (valor.length > 40) valor = valor.slice(0, 40)
        setNuevoColor(valor)
    }

    const manejarArchivo = (e) => {
        const archivo = e.target.files[0] || null
        if (!esArchivoValido(archivo)) {
            setError(MENSAJE_ARCHIVO_INVALIDO)
            setFoto(null)
            e.target.value = ''
            return
        }
        setError('')
        setFoto(archivo)
    }

    const manejarArchivoColor = (e) => {
        const archivo = e.target.files?.[0] ?? null
        if (!esArchivoValido(archivo)) {
            setError(MENSAJE_ARCHIVO_INVALIDO)
            setFotoColor(null)
            e.target.value = ''
            return
        }
        setError('')
        setFotoColor(archivo)
    }

    const manejarDescripcion = (e) => {
        let valor = e.target.value
        if (valor.length > LIMITE_DESCRIPCION) valor = valor.slice(0, LIMITE_DESCRIPCION)
        setForm(f => ({ ...f, descripcion: valor }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        const errorValidacion = validarFormulario(form, esEdicion)
        if (errorValidacion) {
            setError(errorValidacion)
            return
        }
        setError('')
        setCargando(true)
        try {
            let resultado
            if (idCreadoRef.current) {
                resultado = { ...resultadoGuardadoRef.current, id: idCreadoRef.current }
            } else {
                const body = {
                    nombre: form.nombre.trim(),
                    descripcion: form.descripcion?.trim() || null,
                    categoria_id: form.categoria_id,
                    precio: Number(form.precio),
                    stock: Number(form.stock) || 0,
                    material: form.material || null,
                    tamano: form.tamano?.trim() || null,
                    color: form.color?.trim() || null,
                    descuento: form.descuento ? Number(form.descuento) : null,
                    nuevo_lanzamiento: form.nuevo_lanzamiento,
                }
                if (esEdicion) {
                    resultado = await api.patch(`/productos/${producto.id}`, body)
                    resultado.id = producto.id
                } else {
                    resultado = await api.post('/productos', body)
                }
                idCreadoRef.current = resultado.id
                resultadoGuardadoRef.current = resultado
            }

            if (foto && resultado.id && !fotoSubidaRef.current) {
                const fd = new FormData()
                fd.append('imagen', foto)
                await api.post(`/productos/${resultado.id}/imagen`, fd)
                fotoSubidaRef.current = true
            }

            for (const c of coloresPendientes.slice(coloresSubidosRef.current)) {
                await productoApi.guardarColor(resultado.id, c.nombre, c.archivo)
                coloresSubidosRef.current += 1
            }

            onGuardado(resultado)
            onClose()
        } catch (err) {
            setError(err.message || 'Error al guardar')
        } finally {
            setCargando(false)
        }
    }

    return createPortal(
        <div style={overlayStyle}>
            <div
                style={modalStyle}
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    aria-label="Cerrar"
                    style={{
                        position: 'absolute', top: 16, right: 18, background: 'none',
                        border: 'none', color: 'var(--text-dim)', fontSize: 20, cursor: 'pointer',
                        zIndex: 4, lineHeight: 1,
                    }}
                >
                    &times;
                </button>

                <style>{`
                    .modal-scroll::-webkit-scrollbar { width: 6px; }
                    .modal-scroll::-webkit-scrollbar-track { background: transparent; margin: 8px 0; }
                    .modal-scroll::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
                    .modal-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
                    .modal-scroll { scrollbar-gutter: stable; }
                `}</style>

                <div className="modal-scroll" style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
                    <div style={{
                        position: 'sticky', top: 0, zIndex: 3,
                        display: 'flex', flexDirection: 'column',
                        alignItems: 'center', justifyContent: 'center', gap: 10,
                        padding: '15px 52px 13px', background: 'var(--surface)',
                        borderBottom: '1px solid var(--line)',
                    }}>
                        <img src={mediaPath('apolo-vibes-logo.png')} alt="Logo" style={{ height: 60, width: 'auto', marginBottom: -10 }} />
                        <h2 style={{
                            margin: 0, fontSize: 18, fontWeight: 700,
                            color: 'var(--text)', fontFamily: 'var(--font-display)',
                        }}>
                            {esEdicion ? 'Editar producto' : 'Nuevo producto'}
                        </h2>
                    </div>

                    <form id="form-producto" onSubmit={handleSubmit} style={{ padding: '22px 36px 24px' }}>
                        {/* Fila 1: categoria + nombre */}
                        <div style={grid2}>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Categoría *</label>
                                <SelectOpciones
                                    options={categorias.map(c => ({ value: c.id, label: c.nombre }))}
                                    value={form.categoria_id}
                                    onChange={(v) => setForm(f => ({ ...f, categoria_id: v }))}
                                    placeholder="Seleccionar categoría..."
                                />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Nombre *</label>
                                <input autoFocus value={form.nombre} onChange={set('nombre')} style={inputStyle} />
                            </div>
                        </div>

                        {/* Fila 2: precio + descuento + stock */}
                        <div style={grid3}>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>{esEdicion ? 'Precio base (CLP) *' : 'Precio neto (CLP) *'}</label>
                                <input type="number" min={0} step="1" value={form.precio} onChange={set('precio')} style={inputStyle} />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Descuento (%)</label>
                                <input type="text" inputMode='numeric' maxLength={2} value={form.descuento} onChange={manejarDescuento} style={inputStyle} />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Stock</label>
                                <input type="number" min={0} step="1" value={form.stock} onChange={set('stock')} style={inputStyle} />
                            </div>
                        </div>

                        {precioNeto > 0 && (
                            <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: '-4px 0 16px' }}>
                                {esEdicion && desc > 0 && desc < 100 && (
                                    <>Con {desc}% de descuento: </>
                                )}
                                {!esEdicion && desc <= 0 && (
                                    <>Con IVA (19%): ${precioBase.toLocaleString('es-CL')} CLP - se guardará este total</>
                                )}
                                {!esEdicion && desc > 0 && desc < 100 && (
                                    <>Con IVA (19%) y {desc}% de descuento: </>
                                )}
                                {desc > 0 && desc < 100 && (
                                    <>
                                        se guardará{' '}
                                        <span style={{ fontWeight: 700, color: 'var(--text)' }}>
                                            ${precioFinal.toLocaleString('es-CL')} CLP
                                        </span>{' '}
                                        (antes <span style={{ textDecoration: 'line-through', color: 'var(--accent)' }}>
                                            ${precioOriginalPreview.toLocaleString('es-CL')} CLP
                                        </span>)
                                    </>
                                )}
                            </p>
                        )}

                        {/* Fila 3: material + color */}
                        <div style={grid2}>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Material</label>
                                <SelectOpciones
                                    options={MATERIALES}
                                    value={form.material}
                                    onChange={(v) => setForm(f => ({ ...f, material: v }))}
                                    placeholder="Seleccionar..."
                                />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Color</label>
                                <input
                                    value={form.color}
                                    onChange={manejarColor}
                                    placeholder="ej: Azul marino"
                                    style={inputStyle}
                                />
                            </div>
                        </div>

                        {/* Fila 4: tamaño */}
                        <div style={fieldGroup}>
                            <label style={labelStyle}>Tamaño</label>
                            <input value={form.tamano} onChange={set('tamano')} placeholder="ej: 10cm x 8cm" style={inputStyle} />
                        </div>
                        <div style={fieldGroup}>
                            <label style={labelStyle}>Descripción</label>
                            <textarea
                                ref={descripcionRef}
                                value={form.descripcion}
                                onChange={manejarDescripcion}
                                rows={3}
                                style={{
                                    ...inputStyle,
                                    resize: 'none',
                                    overflowY: 'hidden',
                                    fontFamily: 'inherit',
                                    lineHeight: 1.45,
                                }}
                            />
                            <span style={{ fontSize: 11, color: 'var(--text-dim)', display: 'block', textAlign: 'right', marginTop: 4 }}>
                                {form.descripcion.length}/{LIMITE_DESCRIPCION}
                            </span>
                        </div>

                        {!esEdicion && (
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Foto del producto</label>
                                <label
                                    style={{
                                        display: 'flex',
                                        flexDirection: foto ? 'row' : 'column',
                                        alignItems: 'center', justifyContent: foto ? 'flex-start' : 'center',
                                        gap: 12,
                                        border: foto ? '1px solid var(--accent)' : '2px dashed var(--line)',
                                        borderRadius: 10, padding: foto ? '8px' : '24px 20px',
                                        cursor: 'pointer', background: 'var(--bg)',
                                        transition: 'border-color .2s',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                                    onMouseLeave={e => e.currentTarget.style.borderColor = foto ? 'var(--accent)' : 'var(--line)'}
                                >
                                    <input
                                        type="file"
                                        accept={ACEPTAR_IMAGENES}
                                        onChange={manejarArchivo}
                                        style={{ display: 'none' }}
                                    />
                                    {foto ? (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                                            <span style={{
                                                width: 72, height: 72, borderRadius: 8, overflow: 'hidden', flexShrink: 0,
                                                background: 'var(--surface-2)', border: '1px solid var(--line)',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            }}>
                                                {fotoPreview ? (
                                                    <img
                                                        src={fotoPreview}
                                                        alt="Vista previa"
                                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                    />
                                                ) : (
                                                    <Upload size={20} color="var(--text-dim)" strokeWidth={1.5} />
                                                )}
                                            </span>
                                            <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                                                <span style={{
                                                    fontSize: 13, color: 'var(--input-text)', fontWeight: 500,
                                                    overflow: 'hidden', textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap', maxWidth: 240,
                                                }}>
                                                    {foto.name}
                                                </span>
                                                {esRaw(foto.name) && (
                                                    <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                                        Foto RAW - se convertirá a JPEG al guardar
                                                    </span>
                                                )}
                                                <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                                    Click para cambiar imagen
                                                </span>
                                            </span>
                                        </div>
                                    ) : (
                                        <>
                                            <Upload size={24} color="var(--text-dim)" strokeWidth={1.5} style={{ marginBottom: 8 }} />
                                            <span style={{ fontSize: 13, color: 'var(--input-text)', fontWeight: 500 }}>
                                                Haz clic para subir una imagen
                                            </span>
                                        </>
                                    )}
                                </label>
                            </div>
                        )}

                        <div style={fieldGroup}>
                            <label style={labelStyle}>Colores y fotos por color</label>
                            <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: '0 0 10px' }}>
                                Cada color ingresado debe corresponder al color del producto.
                                {!esEdicion && ' Se guardan junto con el producto al crearlo.'}
                            </p>

                            {esEdicion && colores.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                                    {colores.map(c => (
                                        <div
                                            key={c.id}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 10,
                                                padding: 8, border: '1px solid var(--line)',
                                                borderRadius: 10, background: 'var(--bg)',
                                            }}
                                        >
                                            <span style={{
                                                width: 44, height: 44, borderRadius: 8, overflow: 'hidden',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                background: 'var(--surface-2)', flexShrink: 0,
                                            }}>
                                                {c.imagen && (
                                                    <img src={c.imagen} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                                )}
                                            </span>
                                            <span style={{ flex: 1, fontSize: 13, color: 'var(--input-text)' }}>{c.nombre}</span>
                                            <button
                                                type="button"
                                                onClick={() => borrarColor(c.id)}
                                                aria-label={`Quitar color ${c.nombre}`}
                                                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 4 }}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {!esEdicion && coloresPendientes.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                                    {coloresPendientes.map(c => (
                                        <div
                                            key={c.nombre}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 10,
                                                padding: 8, border: '1px dashed var(--line)',
                                                borderRadius: 10, background: 'var(--bg)',
                                            }}
                                        >
                                            <span style={{ flex: 1, fontSize: 13, color: 'var(--input-text)' }}>
                                                {c.nombre}
                                                <span style={{ display: 'block', fontSize: 11, color: 'var(--text-dim)' }}>
                                                    {c.archivo.name.slice(0, 28)}
                                                </span>
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() => quitarColorPendiente(c.nombre)}
                                                aria-label={`Quitar color ${c.nombre}`}
                                                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 4 }}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: 8, alignItems: 'stretch', marginBottom: -15 }}>
                                <input
                                    type="text"
                                    value={nuevoColor}
                                    onChange={manejarNuevoColor}
                                    placeholder="Color"
                                    style={{ ...inputStyle, flex: 1, height: ALTO_CONTROL }}
                                />
                                <label style={{
                                    display: 'flex', alignItems: 'center', gap: 6,
                                    height: ALTO_CONTROL, boxSizing: 'border-box', padding: '0 14px',
                                    border: fotoColor ? '1px solid var(--accent)' : '1px dashed var(--line)',
                                    borderRadius: 8, cursor: 'pointer', fontSize: 11,
                                    color: 'var(--input-text)', whiteSpace: 'nowrap', background: 'var(--bg)',
                                    maxWidth: 200, overflow: 'hidden',
                                }}>
                                    <input
                                        type="file"
                                        accept={ACEPTAR_IMAGENES}
                                        onChange={manejarArchivoColor}
                                        style={{ display: 'none' }}
                                    />
                                    <Upload size={15} color="var(--text-dim)" strokeWidth={1.5} />
                                    {fotoColor ? fotoColor.name.slice(0, 18) : 'Haz clic para subir la imagen'}
                                </label>
                                <button
                                    type="button"
                                    onClick={agregarColor}
                                    disabled={!nuevoColor.trim() || !fotoColor || subiendoColor}
                                    style={{
                                        height: ALTO_CONTROL, boxSizing: 'border-box', padding: '0 16px',
                                        borderRadius: 8, border: 'none', flexShrink: 0,
                                        background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 500,
                                        cursor: (!nuevoColor.trim() || !fotoColor || subiendoColor) ? 'not-allowed' : 'pointer',
                                        opacity: (!nuevoColor.trim() || !fotoColor || subiendoColor) ? 0.5 : 1,
                                    }}
                                >
                                    {subiendoColor ? 'Subiendo...' : 'Agregar'}
                                </button>
                            </div>
                        </div>

                        {/* Switch de lanzamiento. Va al final del form para que el
                            bloque de colores y fotos, que es lo mas largo, no quede
                            corrido hacia abajo. */}
                        <div style={{ ...fieldGroup, marginTop: 18, marginBottom: 0 }}>
                            <button
                                type="button"
                                role="switch"
                                aria-checked={form.nuevo_lanzamiento}
                                onClick={() => setForm(f => ({ ...f, nuevo_lanzamiento: !f.nuevo_lanzamiento }))}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 12, width: '100%',
                                    padding: 12, borderRadius: 10, textAlign: 'left',
                                    border: form.nuevo_lanzamiento ? '1px solid var(--accent)' : '1px solid var(--line)',
                                    background: 'var(--bg)', cursor: 'pointer',
                                    transition: 'border-color .2s',
                                }}
                            >
                                {/* Track del switch. `aria-hidden` porque el estado
                                    ya lo anuncia el aria-checked del boton. */}
                                <span
                                    aria-hidden="true"
                                    style={{
                                        position: 'relative', flexShrink: 0,
                                        width: 42, height: 24, borderRadius: 20,
                                        background: form.nuevo_lanzamiento ? 'var(--accent)' : 'var(--line)',
                                        transition: 'background .2s',
                                    }}
                                >
                                    <span style={{
                                        position: 'absolute', top: 3,
                                        left: form.nuevo_lanzamiento ? 21 : 3,
                                        width: 18, height: 18, borderRadius: '50%',
                                        background: '#fff',
                                        transition: 'left .2s',
                                    }} />
                                </span>
                                <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--input-text)' }}>
                                        Nuevo lanzamiento
                                    </span>
                                    <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                                        Aparece en «Lanzamientos» en la portada, con la etiqueta «Nuevo».
                                    </span>
                                </span>
                            </button>
                        </div>
                    </form>
                    <div style={{
                        position: 'sticky', bottom: 0, zIndex: 3,
                        padding: '14px 36px',
                        background: 'var(--surface)', borderTop: '1px solid var(--line)',
                    }}>
                        {error && (
                            <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 10px' }}>{error}</p>
                        )}

                        <div style={{ display: 'flex', gap: 12 }}>
                            <button type="button" onClick={onClose}
                                style={{
                                    flex: 1, padding: '12px 0', borderRadius: 10, border: '1px solid var(--line)',
                                    background: 'transparent', color: 'var(--text-dim)', fontSize: 14, fontWeight: 500,
                                    cursor: 'pointer', transition: 'border-color .2s',
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
                                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--line)'}
                            >
                                Cancelar
                            </button>
                            <button type="submit" form="form-producto" disabled={cargando || !!errorActual}
                                style={{
                                    flex: 2, padding: '12px 0', borderRadius: 10, border: 'none',
                                    background: 'var(--accent)', color: 'var(--text)', fontSize: 14, fontWeight: 600,
                                    cursor: cargando ? 'default' : 'pointer', display: 'flex',
                                    alignItems: 'center', justifyContent: 'center', gap: 8,
                                    opacity: cargando ? .7 : 1, transition: 'opacity .2s',
                                }}
                            >
                                {cargando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear producto'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>,
        document.body
    )
}
