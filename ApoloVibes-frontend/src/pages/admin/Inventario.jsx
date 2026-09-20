import { useState, useMemo } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { useProductos } from '../../context/ProductContext.jsx';
import { productoApi } from '../../services/products.js';
import ModalProducto from '../../components/ModalProducto.jsx';
import SelectOpciones from '../../components/SelectOpciones.jsx';

export default function Inventario() {
  const { productos, categorias, cargando, recargar, actualizarLocal, eliminarLocal } = useProductos();
  const [modal, setModal] = useState(null);
  const [filtroCat, setFiltroCat] = useState(null);
  const [eliminandoId, setEliminandoId] = useState(null);
  const [mensaje, setMensaje] = useState(null);

  const productosFiltrados = useMemo(() => {
    if (!filtroCat) return productos;
    return productos.filter(p => p.categoria_id === filtroCat);
  }, [productos, filtroCat]);

  const nombreCategoria = (catId) => {
    const cat = categorias.find(c => c.id === catId);
    return cat ? cat.nombre : '—';
  };

  async function eliminarProducto(producto) {
    const confirmado = window.confirm(
      `¿Estás seguro de que deseas eliminar «${producto.nombre}»? Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;

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
            {productosFiltrados.map((p) => (
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
                <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>$ {p.descuento || 0}</td>
                <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{p.stock}</td>
                <td style={{ padding: '13px 10px', color: 'var(--text-dim)', cursor: 'pointer' }} onClick={() => setModal(p)}>
                  <Pencil size={16} color='var(--green)' />
                </td>
                <td
                  style={{ padding: '13px 10px', color: 'var(--text-dim)', cursor: eliminandoId === p.id ? 'wait' : 'pointer' }}
                  onClick={() => !eliminandoId && eliminarProducto(p)}
                  title="Eliminar producto"
                >
                  <Trash2 size={16} color='var(--red)' />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </>
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
    </>
  );
}
