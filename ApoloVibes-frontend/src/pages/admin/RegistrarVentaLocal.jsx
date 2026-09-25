import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, X } from 'lucide-react';
import { useProductos } from '../../context/ProductContext.jsx';
import { ventasApi } from '../../services/ventas.js';

const MEDIOS = ['Efectivo', 'TUU'];

function capitalizar(texto) {
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : '';
}

function formatearFecha(iso) {
  try {
    return capitalizar(new Date(iso).toLocaleDateString('es-CL', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    }));
  } catch {
    return '';
  }
}

function totalVenta(venta) {
  const items = venta.items || [];
  if (items.length) return items.reduce((s, i) => s + Number(i.cantidad) * Number(i.precio_unitario), 0);
  return Number(venta.total) || 0;
}

export default function RegistrarVentaLocal() {
  const { productos, categorias, actualizarLocal } = useProductos();
  const navigate = useNavigate();
  const [sesion, setSesion] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [abriendo, setAbriendo] = useState(false);
  const [registrando, setRegistrando] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [lugar, setLugar] = useState('');
  const [categoriaActual, setCategoriaActual] = useState('');
  const [productoActual, setProductoActual] = useState('');
  const [cantidad, setCantidad] = useState(1);
  const [medioPago, setMedioPago] = useState('');
  const [ticket, setTicket] = useState([]);
  const [ventasDia, setVentasDia] = useState([]);
  const [mostrarCierre, setMostrarCierre] = useState(false);
  const [cerrandoSesion, setCerrandoSesion] = useState(false);

  const fechaHoy = capitalizar(new Date().toLocaleDateString('es-CL', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }));

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const res = await ventasApi.sesionActual();
        if (activo && res) {
          setSesion(res.sesion || null);
          setVentasDia(res.ventas || []);
        }
      } catch (err) {
        if (activo) setMensaje({ tipo: 'error', texto: err.message });
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => { activo = false; };
  }, []);

  async function abrirSesion() {
    setMensaje(null);
    if (!lugar.trim()) {
      setMensaje({ tipo: 'error', texto: 'Indica el lugar de la venta.' });
      return;
    }
    setAbriendo(true);
    try {
      const res = await ventasApi.abrirSesion(lugar.trim());
      const s = res.sesion || null;
      if (!s) throw new Error('No se pudo abrir la sesión.');
      setSesion(s);
      setVentasDia([]);
      setLugar('');
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setAbriendo(false);
    }
  }

  function agregarAlTicket() {
    setMensaje(null);
    const producto = productos.find(p => p.id === productoActual);
    if (!producto) {
      setMensaje({ tipo: 'error', texto: 'Elegí un producto.' });
      return;
    }
    const cant = Number(cantidad);
    if (!cant || cant < 1 || cant > producto.stock) {
      setMensaje({ tipo: 'error', texto: `La cantidad debe estar entre 1 y ${producto.stock}.` });
      return;
    }
    const existente = ticket.find(t => t.producto_id === producto.id);
    if (existente) {
      if (existente.cantidad + cant > producto.stock) {
        setMensaje({ tipo: 'error', texto: `El stock disponible es ${producto.stock}.` });
        return;
      }
      setTicket(ticket.map(t => t.producto_id === producto.id ? { ...t, cantidad: t.cantidad + cant } : t));
    } else {
      setTicket([...ticket, {
        producto_id: producto.id,
        nombre: producto.nombre,
        precio: Number(producto.precio),
        cantidad: cant,
      }]);
    }
    setProductoActual('');
    setCantidad(1);
  }

  function quitarDelTicket(productoId) {
    setTicket(ticket.filter(t => t.producto_id !== productoId));
  }

  async function registrarVenta() {
    setMensaje(null);
    if (!medioPago) {
      setMensaje({ tipo: 'error', texto: 'Elegí el medio de pago.' });
      return;
    }
    if (ticket.length === 0) {
      setMensaje({ tipo: 'error', texto: 'Agregá al menos un producto al ticket.' });
      return;
    }
    setRegistrando(true);
    try {
      if (!sesion || !sesion.id) {
        throw new Error('No hay una sesión de venta activa. Iniciá la sesión primero.');
      }
      const items = ticket.map(t => ({ producto_id: t.producto_id, cantidad: t.cantidad }));
      const res = await ventasApi.registrarVenta(sesion.id, medioPago.toLowerCase(), items);
      const venta = res.venta || res;
      setVentasDia(prev => [...prev, venta]);
      ticket.forEach(t => {
        const producto = productos.find(p => p.id === t.producto_id);
        if (producto) {
          actualizarLocal({ id: t.producto_id, stock: Number(producto.stock) - t.cantidad });
        }
      });
      setTicket([]);
      setProductoActual('');
      setCantidad(1);
      setMedioPago('');
      setMensaje({ tipo: 'ok', texto: 'Venta registrada.' });
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setRegistrando(false);
    }
  }

  async function confirmarCierre() {
    setCerrandoSesion(true);
    setMensaje(null);
    try {
      await ventasApi.cerrarSesion(sesion.id);
      navigate('/admin/reportes');
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
      setMostrarCierre(false);
      setCerrandoSesion(false);
    }
  }


  const totalTicket = ticket.reduce((s, t) => s + t.cantidad * t.precio, 0);
  const totalEfectivo = ventasDia
    .filter(v => (v.medio_pago || '').toLowerCase() === 'efectivo')
    .reduce((s, v) => s + totalVenta(v), 0);
  const totalTuu = ventasDia
    .filter(v => (v.medio_pago || '').toLowerCase() === 'tuu')
    .reduce((s, v) => s + totalVenta(v), 0);
  const totalGeneral = ventasDia.reduce((s, v) => s + totalVenta(v), 0);

  if (!sesion) {
    return (
      <>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Registrar Venta</h1>
        </div>

        {mensaje && (
          <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
            {mensaje.texto}
          </p>
        )}

        <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 16, padding: 28, maxWidth: 420, boxShadow: '0 20px 60px rgba(0,0,0,.08)' }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--surface-2)', marginBottom: 6 }}>
            Lugar de la venta
          </label>
          <input
            value={lugar}
            onChange={(e) => setLugar(e.target.value)}
            placeholder="Ej: Feria de Alameda"
            style={{
              width: '100%', padding: '11px 14px', borderRadius: 10, border: '1px solid var(--line)',
              background: 'var(--surface-3)', color: 'var(--text)', fontSize: 14, boxSizing: 'border-box',
            }}
          />
          <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: '12px 0 18px' }}>Hoy · {fechaHoy}</p>
          <button className="btn btn-primary" onClick={abrirSesion} disabled={abriendo || cargando} style={{ width: '100%', justifyContent: 'center' }}>
            {abriendo ? 'Iniciando…' : 'Iniciar venta'}
          </button>
        </div>
      </>
    );
  }

  const fechaSesion = formatearFecha(sesion.fecha || sesion.creado_en || new Date().toISOString());
  const productosDisponibles = productos.filter(p => !p.sinStock);
  const productosFiltrados = categoriaActual
    ? productosDisponibles.filter(p => p.categoria_id === categoriaActual)
    : productosDisponibles;
  const stockProductoActual = productos.find(p => p.id === productoActual);

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, color: 'var(--surface-2)' }}>Registrar Venta</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{sesion.lugar}</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{fechaSesion}</div>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--green)', marginLeft: -8 }}>
            (Sesión abierta)
          </span>

          <button
            onClick={() => setMostrarCierre(true)}
            style={{
              border: '1px solid var(--red)', background: 'transparent', color: 'var(--red)',
              fontSize: 13, fontWeight: 600, padding: '8px 10px', borderRadius: 10, cursor: 'pointer', marginLeft: 250,
            }}
          >
            Cerrar Ventas
          </button>
        </div>
      </div>

      {mensaje && (
        <p style={{ color: mensaje.tipo === 'ok' ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)', margin: '0 0 16px', fontSize: 13 }}>
          {mensaje.texto}
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24, alignItems: 'start' }}>
        <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 16, padding: 22 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 16, color: 'var(--surface-2)', margin: '0 0 16px' }}>Nueva venta</h2>
          <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
            <select
              value={categoriaActual}
              onChange={(e) => { setCategoriaActual(e.target.value); setProductoActual(''); }}
              style={{
                flex: 1, padding: '10px 12px', borderRadius: 10, border: '1px solid var(--line)',
                background: 'var(--surface-3)', color: 'var(--surface)', fontSize: 13,
              }}
            >
              <option value="">Todas las categorías</option>
              {categorias.filter(c => c.cantidad > 0).map(c => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
            <select
              value={productoActual}
              onChange={(e) => setProductoActual(e.target.value)}
              style={{
                flex: 1, padding: '10px 12px', borderRadius: 10, border: '1px solid var(--line)',
                background: 'var(--surface-3)', color: 'var(--surface)', fontSize: 13,
              }}
            >
              <option value="">Selecciona un producto</option>
              {productosFiltrados.map(p => (
                <option key={p.id} value={p.id}>
                  {p.nombre} — ${p.precio.toLocaleString('es-CL')}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              max={stockProductoActual ? stockProductoActual.stock : 1}
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              style={{
                width: 90, padding: '10px 12px', borderRadius: 10, border: '1px solid var(--line)',
                background: 'var(--surface-3)', color: 'var(--surface)', fontSize: 13,
              }}
            />
          </div>
          <button className="btn btn-primary" onClick={agregarAlTicket} style={{ width: '100%', justifyContent: 'center' }}>
            + Agregar productos
          </button>
        </div>

        <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 16, padding: 22 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 16, color: 'var(--surface-2)', margin: '0 0 16px' }}>Carrito</h2>
          {ticket.length === 0 ? (
            <p style={{ color: 'var(--text-dim)', fontSize: 13, textAlign: 'center', marginBottom: 15 }}>No hay productos aún.</p>
          ) : (
            <>
              {ticket.map((t) => (
                <div
                  key={t.producto_id}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--surface-3)', fontSize: 13 }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ color: 'var(--surface-2)', fontWeight: 500 }}>{t.nombre} ( {t.cantidad} )</div>
                    <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>${t.precio.toLocaleString('es-CL')}
                    </div>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface-2)', fontWeight: 600 }}>
                    ${(t.cantidad * t.precio).toLocaleString('es-CL')}
                  </div>
                  <button
                    onClick={() => quitarDelTicket(t.producto_id)}
                    aria-label="Quitar del ticket"
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 4 }}
                  >
                    <Trash2 size={16} color="var(--red)" />
                  </button>
                </div>
              ))}
              <div style={{ marginTop: 8, paddingTop: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', fontSize: 12, color: 'var(--text-dim)', marginBottom: -10 }}>
                  <span>IVA (19%)</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>${Math.round(totalTicket * 0.19).toLocaleString('es-CL')}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0 4px', fontSize: 14, fontWeight: 700, color: 'var(--surface-2)' }}>
                  <span>Total</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>${Math.round(totalTicket * 1.19).toLocaleString('es-CL')}</span>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--surface-3)', margin: '8px 0' }} />
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--surface-2)', marginBottom: 8 }}>Medio de pago</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {MEDIOS.map((medio) => {
                    const activo = medioPago === medio;
                    return (
                      <button
                        key={medio}
                        onClick={() => setMedioPago(medio)}
                        style={{
                          padding: '8px 18px', borderRadius: 999, fontSize: 13, fontWeight: 600,
                          border: activo ? '1px solid var(--green)' : '1px solid var(--line)',
                          background: activo ? 'var(--green)' : 'transparent',
                          color: activo ? 'var(--text)' : 'var(--surface-2)', cursor: 'pointer',
                        }}
                      >
                        {medio}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
          <button
            className="btn btn-primary"
            onClick={registrarVenta}
            style={{ width: '100%', padding: '10px 0', fontSize: 15, marginTop: 4, justifyContent: 'center' }}
          >
            Registrar venta
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface-3)', border: '1px solid var(--line)', borderRadius: 16, padding: 22, marginTop: 24 }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 16, color: 'var(--surface-2)', margin: '0 0 16px' }}>Ventas del día</h2>
        {ventasDia.length === 0 ? (
          <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Aún no hay ventas registradas hoy.</p>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--surface)', textAlign: 'left', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '0 10px 12px' }}>Hora</th>
                  <th style={{ padding: '0 10px 12px' }}>Medio de pago</th>
                  <th style={{ padding: '0 10px 12px' }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {ventasDia.map((venta, i) => (
                  <tr key={venta.id || i} style={{ borderTop: '1px solid var(--surface-3)' }}>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>
                      {new Date(venta.creado_en).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td style={{ padding: '13px 10px', color: 'var(--text-dim)' }}>{capitalizar(venta.medio_pago)}</td>
                    <td style={{ padding: '13px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                      ${totalVenta(venta).toLocaleString('es-CL')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ borderTop: '1px solid var(--surface-3)', marginTop: 8, paddingTop: 14, display: 'flex', gap: 18, justifyContent: 'center', flexWrap: 'wrap', fontSize: 13 }}>
              <span style={{ color: 'var(--text-dim)' }}>
                N° ventas <strong style={{ color: 'var(--surface-2)', fontFamily: 'var(--font-mono)' }}></strong>
              </span>
              <span style={{ color: 'var(--text-dim)' }}>
                Efectivo <strong style={{ color: 'var(--surface-2)', fontFamily: 'var(--font-mono)' }}>${totalEfectivo.toLocaleString('es-CL')}</strong>
              </span>
              <span style={{ color: 'var(--text-dim)' }}>
                TUU <strong style={{ color: 'var(--surface-2)', fontFamily: 'var(--font-mono)' }}>${totalTuu.toLocaleString('es-CL')}</strong>
              </span>
              <span style={{ color: 'var(--text-dim)' }}>
                Total <strong style={{ color: 'var(--green)', fontFamily: 'var(--font-mono)' }}>${totalGeneral.toLocaleString('es-CL')}</strong>
              </span>
            </div>
          </>
        )}
      </div>

      {mostrarCierre && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.49)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, backdropFilter: 'blur(4px)',
          }}
          onClick={() => !cerrandoSesion && setMostrarCierre(false)}
        >
          <div
            style={{
              background: 'var(--surface)', borderRadius: 16, padding: '32px 28px',
              width: '100%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,.3)',
              textAlign: 'center',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
              Cerrar sesión
            </h3>
            <p style={{ margin: '0 0 22px', fontSize: 13, color: 'var(--text-dim)' }}>
              Se guardará el reporte de ventas y no podrás registrar más ventas en esta sesión. ¿Seguro?
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() => setMostrarCierre(false)}
                disabled={cerrandoSesion}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, border: '1px solid var(--line)',
                  background: 'transparent', color: 'var(--text)', fontSize: 13, fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
              <button
                onClick={confirmarCierre}
                disabled={cerrandoSesion}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
                  background: '#b60303', color: '#fff', fontSize: 13, fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {cerrandoSesion ? 'Cerrando…' : 'Sí, cerrar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}