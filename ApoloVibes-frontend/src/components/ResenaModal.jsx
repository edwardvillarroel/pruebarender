import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { pedidosApi } from '../services/orders.js';
import { useToast } from '../context/ToastContext.jsx';
import { useProductos } from '../context/ProductContext.jsx';
import { mediaPath } from '../utils/media.js';
import { useBloqueoScroll } from '../hooks/useBloqueoScroll.js';


const MAX_COMENTARIO = 300;
const CARACTERES_NO_PERMITIDOS = /[^\p{L}\p{N}\s.,;:!?¡¿()'"-]/gu;

function sanitizarComentario(valor){
  return String(valor ?? '')
  .normalize('NFC')
  .replace(CARACTERES_NO_PERMITIDOS, '')
  .replace(/[ \t]{2,}/g, ' ')
  .replace(/\n{3,}/g, '\n\n')
  .slice(0, MAX_COMENTARIO)
}

function productosUnicos(items) {
  const vistos = new Set();
  return (items || []).filter((item) => {
    if (!item.producto_id || vistos.has(item.producto_id)) return false;
    vistos.add(item.producto_id);
    return true;
  });
}

export default function ResenaModal({ pedido, onClose }) {
  const mostrarToast = useToast();
  const { recargar } = useProductos();
  useBloqueoScroll();
  const productos = productosUnicos(pedido.items);
  const [estrellas, setEstrellas] = useState({});
  const [yaResenados, setYaResenados] = useState({}); 
  const [comentarios, setComentarios] = useState({});
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const data = await pedidosApi.resenas(pedido.id);
        if (!vivo) return;
        const marcados = {};
        const cargados = {};
        const textos = {};
        (data.resenas || []).forEach((r) => {
          marcados[r.producto_id] = Number(r.estrellas);
          cargados[r.producto_id] = Number(r.estrellas);
          textos[r.producto_id] = r.comentario ?? '';
        });
        setYaResenados(marcados);
        setEstrellas(cargados);
        setComentarios(textos);
      } catch (err) {
        if (vivo) setError(err.message);
      } finally {
        if (vivo) setCargando(false);
      }
    })();
    return () => { vivo = false; };
  }, [pedido.id]);

  async function enviar() {
    const pendientes = productos.filter(
      (item) => yaResenados[item.producto_id] === undefined && (estrellas[item.producto_id] || 0) > 0
    );
    if (pendientes.length === 0) return;

    setEnviando(true);
    setError(null);
    let fallidos = 0;
    let ultimoError = null;
    for (const item of pendientes) {
      const texto = sanitizarComentario(comentarios[item.producto_id]).trim();
      try {
        await pedidosApi.resenar(pedido.id, item.producto_id, estrellas[item.producto_id], texto || null);
      } catch (err) {
        fallidos += 1;
        ultimoError = err.message;
      }
    }
    setEnviando(false);

    if (fallidos === 0) {
      mostrarToast(`¡Gracias! Enviaste ${pendientes.length} valoración${pendientes.length === 1 ? '' : 'es'}.`);
      recargar();
      onClose();
    } else {
      const exitosos = pendientes.length - fallidos;
      setError(ultimoError || 'No se pudieron enviar todas las valoraciones.');
      if (exitosos > 0) {
        mostrarToast(`${exitosos} de ${pendientes.length} valoraciones enviadas.`, 'error');
        recargar(); 
        try {
          const data = await pedidosApi.resenas(pedido.id);
          const marcados = {};
          const textos = {};
          (data.resenas || []).forEach((r) => {
            marcados[r.producto_id] = Number(r.estrellas);
            textos[r.producto_id] = r.comentario ?? '';
          });
          setYaResenados(marcados);
          setEstrellas((prev) => ({ ...marcados, ...prev }));
          setComentarios((prev) => ({ ...prev, ...textos }));
        } catch {
        }
      }
    }
  }

  const hayPendientes = productos.some(
    (item) => yaResenados[item.producto_id] === undefined && (estrellas[item.producto_id] || 0) > 0
  );

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
          width: '100%', maxWidth: 560, boxShadow: '0 20px 60px rgba(0,0,0,.3)', 
          textAlign: 'left', maxHeight: '86vh', overflowY: 'auto', boxSizing: 'border-box',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <img src={mediaPath('statsApolo.webp')} alt="Logo" loading="lazy" decoding="async" width="512" height="512" style={{ display: 'block', height: 100, width: 'auto', margin: '0 auto 10px' }}/>
        <h3 style={{ margin: '0 0 10px', fontSize: 18, fontWeight: 700, color: 'var(--text)', textAlign: 'center' }}>
          Valorar Nuestro producto
        </h3>
        <div className="separador-suave" style={{ marginBottom: 18 }} />
        <p style={{ margin: '0 0 16px', fontSize: 12, color: 'var(--text-dim)', textAlign: 'center' }}>
          ¿Quedaste conforme con nuestros productos? Agradeceriamos mucho si pudieras valorar nuestros productos. Elige cuántas estrellas quieres darle a cada producto de tu pedido.
        </p>

        {error && (
          <p style={{ color: 'var(--red, #ef4444)', fontSize: 13, margin: '0 0 12px' }}>
            {error}
          </p>
        )}

        {cargando ? (
          <p style={{ color: 'var(--text-dim)', fontSize: 13, textAlign: 'center', marginBottom: 30 }}>Cargando…</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 20 }}>
            {productos.map((item) => {
              const bloqueado = yaResenados[item.producto_id] !== undefined;
              const valor = estrellas[item.producto_id] || 0;
              return (
                <div
                  key={item.producto_id}
                  style={{
                    display: 'flex', flexDirection: 'column', gap: 8,
                    padding: '10px 12px', borderRadius: 10, border: '1px solid var(--surface-3)',
                    opacity: bloqueado ? 0.6 : 1, backgroundColor: 'var(--bg)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ fontSize: 13, color: 'var(--accent)', minWidth: 0 }}>
                      {item.nombre || 'Producto'}
                      {item.color && (
                        <span style={{ color: 'var(--surface)' }}> · {item.color}</span>
                      )}
                      {bloqueado && (
                        <span style={{ display: 'block', fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                          Ya valorado
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                      {Array.from({ length: 5 }).map((_, i) => {
                        const n = i + 1;
                        return (
                          <button
                            key={n}
                            type="button"
                            disabled={bloqueado || enviando}
                            onClick={() => setEstrellas((prev) => ({ ...prev, [item.producto_id]: n }))}
                            title={bloqueado ? 'Producto ya valorado' : `${n} estrella${n === 1 ? '' : 's'}`}
                            style={{
                              background: 'none', border: 'none', padding: 2, cursor: bloqueado || enviando ? 'not-allowed' : 'pointer',
                            }}
                          >
                            <Star
                              size={20}
                              fill={i < valor ? '#FA7F19' : 'none'}
                              color={i < valor ? '#FA7F19' : 'var(--line)'}
                            />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <textarea
                    value={comentarios[item.producto_id] ?? ''}
                    onChange={(e) => setComentarios((prev) => ({ ...prev, [item.producto_id]: sanitizarComentario(e.target.value) }))}
                    placeholder="Escribe tu reseña (opcional)"
                    maxLength={MAX_COMENTARIO}
                    disabled={enviando || !!yaResenados[item.producto_id]}
                    style={{
                      width: '100%', boxSizing: 'border-box', textAlign: 'left',
                      border: '1px solid var(--line)', background: 'var(--surface-3)',
                      color: 'var(--surface)', borderRadius: 10, padding: '10px 12px',
                      fontFamily: 'inherit', fontSize: 13, resize: 'vertical', minHeight: 64,
                      outline: 'none', opacity: enviando || yaResenados[item.producto_id] ? 0.6 : 1,
                    }}
                  />
                </div>
              );
            })}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
              backgroundColor: 'var(--accent)', color: 'var(--text)', fontSize: 13, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Cerrar
          </button>
          <button
            onClick={enviar}
            disabled={cargando || enviando || !hayPendientes}
            style={{
              flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
              backgroundColor: 'var(--green, #16bd10)', color: '#06210f', fontSize: 13, fontWeight: 600,
              cursor: cargando || enviando || !hayPendientes ? 'not-allowed' : 'pointer',
              opacity: cargando || enviando || !hayPendientes ? 0.6 : 1,
            }}
          >
            {enviando ? 'Enviando…' : 'Enviar valoración'}
          </button>
        </div>
      </div>
    </div>
  );
}
