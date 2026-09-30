import { useState, useMemo, useEffect } from 'react';
import { Pencil, Trash2, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react';
import { useProductos } from '../../context/ProductContext.jsx';
import { productoApi } from '../../services/products.js';
import ModalProducto from '../../components/ModalProducto.jsx';
import SelectOpciones from '../../components/SelectOpciones.jsx';
import { mediaPath } from '../../utils/media.js';

function ConfirmEliminarModal({ producto, onConfirm, onCancel }) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          textAlign: 'center',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 10 }}>
          <img src={mediaPath('apolo-vibes-logo.png')} alt="Logo" style={{ width: 60, height: 60, marginBottom: -5 }} />
        </div>
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
          Eliminar producto
        </h3>
        <p style={{ margin: '0 0 22px', fontSize: 13, color: 'var(--text-dim)' }}>
          ¿Estás seguro de que deseas eliminar <strong>«{producto.nombre}»</strong>? Esta acción no se puede deshacer.
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
              background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
              background: '#b60303', color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Sí, eliminar
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Inventario() {
  const { productos, categorias, cargando, recargar, actualizarLocal, eliminarLocal } = useProductos();
  const [modal, setModal] = useState(null);
  const [filtroCat, setFiltroCat] = useState(null);
  const [eliminandoId, setEliminandoId] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [filasPorPagina, setFilasPorPagina] = useState(6);
  const [productoEliminar, setProductoEliminar] = useState(null);

  useEffect(() => {
    recargar()
  }, [])

  useEffect(() => {
    const calcularFilas = () => {
      const disponible = window.innerHeight - 320;
      const base = Math.floor(disponible / 45);
      const maximo = window.innerWidth < 768 ? 6 : 10;
      setFilasPorPagina(Math.max(3, Math.min(base, maximo)));
    };
    calcularFilas();
    window.addEventListener('resize', calcularFilas);
    return () => window.removeEventListener('resize', calcularFilas);
  }, []);

  const productosFiltrados = useMemo(() => {
    if (!filtroCat) return productos;
    return productos.filter(p => p.categoria_id === filtroCat);
  }, [productos, filtroCat]);

  useEffect(() => {
    setPagina(1);
  }, [filtroCat]);

  const totalPaginas = Math.max(1, Math.ceil(productosFiltrados.length / filasPorPagina));

  useEffect(() => {
    if (pagina > totalPaginas) setPagina(totalPaginas);
  }, [totalPaginas, pagina]);

  const productosPagina = useMemo(() => {
    const inicio = (pagina - 1) * filasPorPagina;
    return productosFiltrados.slice(inicio, inicio + filasPorPagina);
  }, [productosFiltrados, pagina, filasPorPagina])

  const nombreCategoria = (catId) => {
    const cat = categorias.find(c => c.id === catId);
    return cat ? cat.nombre : '—';
  };

  async function eliminarProducto(producto) {
    setProductoEliminar(null);
    setEliminandoId(producto.id);
    setMensaje(null);
    try {
      await productoApi.eliminar(producto.id);
      eliminarLocal(producto.id);
      setMensaje({ tipo: 'ok', texto: 'Producto eliminado correctamente.' });
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setEliminandoId(null);
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Inventario</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 200 }}>
            <SelectOpciones
              options={[{ value: '', label: 'Todas las categorías' }, ...categorias.map(c => ({ value: c.id, label: c.nombre }))]}
              value={filtroCat || ''}
              onChange={(v) => setFiltroCat(v || null)}
              placeholder="Todas las categorías"
            />
          </div>
          <button className="btn btn-primary" onClick={() => setModal('nuevo')}>+ Nuevo producto</button>
        </div>
      </div>

      {cargando ? (
        <p style={{ color: 'var(--text-dim)' }}>Cargando inventario…</p>
      ) : productos.length === 0 ? (
        <p style={{ color: 'var(--text-dim)' }}>No hay productos en la base de datos.</p>
      ) : (
        <>
          {mensaje && (
            <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
              {mensaje.texto}
            </p>
          )}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '0 10px 12px' }}>#</th>
                  <th style={{ padding: '0 10px 12px' }}>Categoría</th>
                  <th style={{ padding: '0 10px 12px' }}>Nombre</th>
                  <th style={{ padding: '0 10px 12px' }}>Descripción</th>
                  <th style={{ padding: '0 10px 12px' }}>Material</th>
                  <th style={{ padding: '0 10px 12px' }}>Tamaño</th>
                  <th style={{ padding: '0 10px 12px' }}>Color</th>
                  <th style={{ padding: '0 10px 12px' }}>Precio</th>
                  <th style={{ padding: '0 10px 12px' }}>Descuento</th>
                  <th style={{ padding: '0 10px 12px' }}>Stock</th>
                  <th style={{ padding: '0 10px 12px' }}></th>
                  <th style={{ padding: '0 10px 12px' }}></th>
                </tr>
              </thead>
              <tbody>
                {productosPagina.map((p) => (
                  <tr key={p.id} style={{ borderTop: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: 11 }}>{p.id?.slice(0, 8)}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{nombreCategoria(p.categoria_id)}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.nombre}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)', maxWidth: 200 }}>
                      <div style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {p.descripcion || '—'}
                      </div>
                    </td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.material || '—'}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.tamano || '—'}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.color || '—'}</td>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>${p.precio.toLocaleString('es-CL')}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.descuento || 0}%</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.stock}</td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)', cursor: 'pointer' }} onClick={() => setModal(p)}>
                      <Pencil size={16} color='var(--green)' />
                    </td>
                    <td
                      style={{ padding: '13px 10px', color: 'var(--text-dim)', cursor: eliminandoId === p.id ? 'wait' : 'pointer' }}
                      onClick={() => !eliminandoId && setProductoEliminar(p)}
                      title="Eliminar producto"
                    >
                      <Trash2 size={16} color='var(--red)' />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {productosFiltrados.length > 0 && (
        <div
          style={{
            position: 'sticky', bottom: 0, zIndex: 10,
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            marginTop: 'auto', gap: 8, padding: '20px 16px 12px',
            background: 'var(--bg)', borderTop: '1px solid var(--surface-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-dim)' }}>
            <button
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={pagina === 1}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 30, height: 30, borderRadius: 8, border: '1px solid var(--surface-3)',
                background: 'transparent', color: 'var(--text-dim)',
                cursor: pagina === 1 ? 'not-allowed' : 'pointer',
                opacity: pagina === 1 ? 0.4 : 1,
              }}
              aria-label="Página anterior"
            >
              <ChevronLeft size={15} />
            </button>

            <span style={{ padding: '0 8px', fontFamily: 'var(--font-mono)' }}>
              {pagina} / {totalPaginas}
            </span>

            <button
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={pagina === totalPaginas}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 30, height: 30, borderRadius: 8, border: '1px solid var(--surface-3)',
                background: 'transparent', color: 'var(--text-dim)',
                cursor: pagina === totalPaginas ? 'not-allowed' : 'pointer',
                opacity: pagina === totalPaginas ? 0.4 : 1,
              }}
              aria-label="Página siguiente"
            >
              <ChevronRight size={15} />
            </button>
          </div>

          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            Mostrando {(pagina - 1) * filasPorPagina + 1}
            –{Math.min(pagina * filasPorPagina, productosFiltrados.length)} de {productosFiltrados.length}
          </span>
        </div>
      )}

      {modal && (
        <ModalProducto
          producto={modal === 'nuevo' ? null : modal}
          categorias={categorias}
          onClose={() => setModal(null)}
          onGuardado={(datos) => {
            if (modal === 'nuevo') {
              recargar()
            } else {
              actualizarLocal(datos)
            }
          }}
        />
      )}

      {productoEliminar && (
        <ConfirmEliminarModal
          producto={productoEliminar}
          onConfirm={() => eliminarProducto(productoEliminar)}
          onCancel={() => setProductoEliminar(null)}
        />
      )}
    </>
  );
}
