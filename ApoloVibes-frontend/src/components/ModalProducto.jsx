import { useState, useLayoutEffect, useMemo, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../services/api.js'
import SelectOpciones from './SelectOpciones.jsx'
import { Upload } from 'lucide-react'

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

const MATERIALES = ['PLA', 'Resina UV', 'PETG', 'ABS', 'TPU', 'Madera', 'Metal', 'Otros']
const COLORES = ['Blanco', 'Negro', 'Rojo', 'Azul', 'Verde', 'Amarillo', 'Naranja', 'Rosa', 'Gris', 'Transparente', 'Otro']

export default function ModalProducto({ producto, categorias, onClose, onGuardado }) {
    const esEdicion = !!producto

    const [form, setForm] = useState({
        nombre: producto?.nombre || '',
        descripcion: producto?.descripcion || '',
        categoria_id: producto?.categoria_id || (categorias[0]?.id ?? ''),
        precio: producto?.precio ?? '',
        stock: producto?.stock ?? '',
        material: producto?.material || '',
        tamano: producto?.tamano || '',
        color: producto?.color || '',
        descuento: producto?.descuento ?? '',
    })
    const [foto, setFoto] = useState(null)
    const [fotoPreview, setFotoPreview] = useState(null)
    const [error, setError] = useState('')
    const [cargando, setCargando] = useState(false)

    useEffect(() => {
        if (foto) {
            const url = URL.createObjectURL(foto)
            setFotoPreview(url)
            return () => URL.revokeObjectURL(url)
        }
        setFotoPreview(null)
    }, [foto])

    const precioOriginalPreview = useMemo(() => {
        const precio = Number(form.precio) || 0
        const desc = Number(form.descuento) || 0
        if (precio <= 0 || desc <= 0 || desc >= 100) return null
        return Math.ceil(precio / (1 - desc / 100))
    }, [form.precio, form.descuento])

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

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!form.nombre || !form.categoria_id || !form.precio) {
            setError('Nombre, categoría y precio son obligatorios')
            return
        }
        setError('')
        setCargando(true)
        try {
            const body = {
                nombre: form.nombre,
                descripcion: form.descripcion || null,
                categoria_id: form.categoria_id,
                precio: Number(form.precio),
                stock: Number(form.stock) || 0,
                material: form.material || null,
                tamano: form.tamano || null,
                color: form.color || null,
                descuento: form.descuento ? Number(form.descuento) : null,
            }
            let resultado
            if (esEdicion) {
                resultado = await api.patch(`/productos/${producto.id}`, body)
                resultado.id = producto.id
            } else {
                resultado = await api.post('/productos', body)
            }

            if (foto && resultado.id) {
                const fd = new FormData()
                fd.append('imagen', foto)
                await api.post(`/productos/${resultado.id}/imagen`, fd)
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
                        zIndex: 2, lineHeight: 1,
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

                <div className="modal-scroll" style={{ overflowY: 'auto', flex: 1, minHeight: 0, padding: '40px 36px' }}>
                    <h2 style={{ margin: '0 0 24px', fontSize: 20, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-display)', textAlign: 'center' }}>
                        {esEdicion ? 'Editar producto' : 'Nuevo producto'}
                    </h2>

                    <form onSubmit={handleSubmit}>
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

                        <div style={fieldGroup}>
                            <label style={labelStyle}>Descripción</label>
                            <textarea value={form.descripcion} onChange={set('descripcion')} rows={3}
                                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Precio (CLP) *</label>
                                <input type="number" value={form.precio} onChange={set('precio')} style={inputStyle} />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Stock</label>
                                <input type="number" value={form.stock} onChange={set('stock')} style={inputStyle} />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
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
                                <SelectOpciones
                                    options={COLORES}
                                    value={form.color}
                                    onChange={(v) => setForm(f => ({ ...f, color: v }))}
                                    placeholder="Seleccionar..."
                                />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Tamaño</label>
                                <input value={form.tamano} onChange={set('tamano')} placeholder="ej: 10cm x 8cm" style={inputStyle} />
                            </div>
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Descuento (%)</label>
                                <input type="number" min={0} max={99} value={form.descuento} onChange={set('descuento')} style={inputStyle} />
                            </div>
                        </div>

                        {precioOriginalPreview && (
                            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 16px' }}>
                                Precio original: <span style={{ textDecoration: 'line-through', color: 'var(--accent)' }}>
                                    ${precioOriginalPreview.toLocaleString('es-CL')} CLP
                                </span>
                            </p>
                        )}

                        {!esEdicion && (
                            <div style={fieldGroup}>
                                <label style={labelStyle}>Foto del producto</label>
                                <label
                                    style={{
                                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                        border: foto ? '1px solid var(--accent)' : '2px dashed var(--line)',
                                        borderRadius: 10, padding: foto ? '16px 20px' : '32px 20px',
                                        cursor: 'pointer', background: 'var(--bg)',
                                        transition: 'border-color .2s',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                                    onMouseLeave={e => e.currentTarget.style.borderColor = foto ? 'var(--accent)' : 'var(--line)'}
                                >
                                    <input
                                        type="file"
                                        accept="image/*"
                                        onChange={(e) => setFoto(e.target.files[0] || null)}
                                        style={{ display: 'none' }}
                                    />
                                    {foto && fotoPreview ? (
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                                            <img
                                                src={fotoPreview}
                                                alt="Vista previa"
                                                style={{ maxWidth: '100%', maxHeight: 180, borderRadius: 8, objectFit: 'contain' }}
                                            />
                                            <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                                                Click para cambiar imagen
                                            </span>
                                        </div>
                                    ) : foto ? (
                                        <>
                                            <span style={{ fontSize: 13, color: 'var(--input-text)', fontWeight: 500 }}>
                                                {foto.name}
                                            </span>
                                            <span style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                                                Click para cambiar imagen
                                            </span>
                                        </>
                                    ) : (
                                        <>
                                            <Upload size={28} color="var(--text-dim)" strokeWidth={1.5} style={{ marginBottom: 8 }} />
                                            <span style={{ fontSize: 13, color: 'var(--input-text)', fontWeight: 500, marginBottom: 2 }}>
                                                Haz clic para subir una imagen
                                            </span>
                                        </>
                                    )}
                                </label>
                            </div>
                        )}

                        {error && (
                            <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 14px' }}>{error}</p>
                        )}

                        <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
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
                            <button type="submit" disabled={cargando}
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
                    </form>
                </div>
            </div>
        </div>,
        document.body
    )
}
