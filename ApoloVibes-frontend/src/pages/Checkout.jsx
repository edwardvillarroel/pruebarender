import { useState } from 'react'
import { mediaPath } from '../utils/media.js'
import { Navigate, Link } from 'react-router-dom'
import { useCart } from '../context/CartContext.jsx'
import { iniciarPago } from '../services/payment.js'
import SelectOpciones from '../components/SelectOpciones.jsx'


const ENVIO_GRATIS_DESDE = 50000
const COSTO_ENVIO_ESTANDAR = 5990

const REGIONES = [
  'Valparaíso',
  'Metropolitana de Santiago',
  'Biobío',
  'La Araucanía',
]

const COMUNAS_POR_REGION = {
  'Valparaíso': ['Viña del Mar', 'Valparaíso', 'Quilpué', 'Villa Alemana'],
  'Metropolitana de Santiago': ['Santiago', 'Providencia', 'Las Condes', 'Ñuñoa'],
  'Biobío': ['Concepción', 'Talcahuano', 'Chiguayante'],
  'La Araucanía': ['Temuco', 'Padre Las Casas'],
}

const emailValido = valor => /\S+@\S+\.\S+/.test(valor)
const telefonoValido = valor => /^\d{8}$/.test(valor)

function rutValido(rutSucio) {
  const rut = rutSucio.replace(/[.\s]/g, '').toUpperCase()
  if (!/^\d{7,8}-[0-9K]$/.test(rut)) return false

  const [cuerpo, dv] = rut.split('-')
  let suma = 0
  let multiplicador = 2

  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += Number(cuerpo[i]) * multiplicador
    multiplicador = multiplicador === 7 ? 2 : multiplicador + 1
  }

  const resto = 11 - (suma % 11)
  const dvEsperado = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto)

  return dv === dvEsperado
}

// Mensaje de error diferenciado: formato vs. dígito verificador.
function rutMensajeError(cliente) {
  if (cliente.tipoIdentificacion !== 'rut') return ''
  const rut = cliente.rut.trim()
  if (!rut) return ''
  if (!/^\d{7,8}-[0-9K]$/.test(rut.replace(/[.\s]/g, '').toUpperCase())) {
    return 'Ingresa tu RUT sin puntos y con guión. Ejemplos: 12345678-K, 1234567-9'
  }
  if (!rutValido(rut)) {
    return 'El dígito verificador no es válido. Revisa el RUT ingresado.'
  }
  return ''
}

export default function Checkout() {
  const { items, total } = useCart()
  const [cliente, setCliente] = useState({
    email: '',
    nombre: '',
    apellido: '',
    region: '',
    comuna: '',
    codigoPostal: '',
    direccion: '',
    numero: '',
    dpto: '',
    ciudad: '',
    telefono: '',
    tipoDocumento: '',
    tipoIdentificacion: '',
    rut: '',
    razonSocial: '',
    giro: '',
  })
  const [guardarDatos, setGuardarDatos] = useState(false)
  const [facturacionIgual, setFacturacionIgual] = useState(true)
  const [mayorEdad, setMayorEdad] = useState(true)
  const [aceptaTerminos, setAceptaTerminos] = useState(false)
  const [entrega, setEntrega] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  if (items.length === 0) {
    return <Navigate to="/carrito" replace />
  }

  const contactoCompleto = emailValido(cliente.email)

  const direccionCompleta =
    contactoCompleto &&
    cliente.nombre.trim() &&
    cliente.apellido.trim() &&
    cliente.region &&
    cliente.comuna &&
    cliente.codigoPostal &&
    cliente.direccion.trim() &&
    cliente.ciudad.trim() &&
    telefonoValido(cliente.telefono)

  const telefonoError =
    cliente.telefono.trim() && !telefonoValido(cliente.telefono)
      ? 'Ingrese un teléfono móvil válido, por ejemplo 1234 5678.'
      : ''

  const rutError = rutMensajeError(cliente)

  const identificacionValida =
    cliente.tipoIdentificacion === 'rut'
      ? rutValido(cliente.rut)
      : cliente.tipoIdentificacion === 'pasaporte'
        ? cliente.rut.trim().length > 0
        : false

  const facturaCompleta =
    cliente.tipoDocumento !== 'factura' ||
    (cliente.razonSocial.trim() && cliente.giro.trim())

  const datosPersonalesCompletos =
    direccionCompleta &&
    cliente.tipoDocumento &&
    identificacionValida &&
    facturaCompleta &&
    mayorEdad &&
    aceptaTerminos

  const entregaSeleccionada = datosPersonalesCompletos && entrega !== null

  const costoEnvio = entrega === 'retiro' ? 0 : entrega === 'envio' ? (total >= ENVIO_GRATIS_DESDE ? 0 : COSTO_ENVIO_ESTANDAR) : 0
  const totalFinal = total + costoEnvio
  const montoNeto = Math.round(totalFinal / 1.19)
  const montoIva = totalFinal - montoNeto

  function actualizar(campo, valor) {
    setCliente(prev => ({ ...prev, [campo]: valor }))
  }

  function cambiarRegion(valor) {
    setCliente(prev => ({ ...prev, region: valor, comuna: '' }))
  }

  async function pagar(e) {
    e.preventDefault()
    setError(null)

    if (!entregaSeleccionada) {
      setError('Completa todos los pasos antes de continuar.')
      return
    }

    setEnviando(true)
    try {
      const clienteEnvio = cliente.telefono.trim()
        ? { ...cliente, telefono: '+569' + cliente.telefono.trim() }
        : cliente
      await iniciarPago({ items, total: totalFinal, cliente: clienteEnvio, entrega })
    } catch (err) {
      setError('No pudimos iniciar el pago. Intenta nuevamente.')
      setEnviando(false)
    }
  }

  return (
    <section className="wrap" style={{ paddingTop: '48px', paddingBottom: '80px' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <img src={mediaPath('nombrelogo.png')} alt='logo' className='nombre-logo'></img>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
          ({items.length} {items.length === 1 ? 'producto' : 'productos'}) &nbsp; ${totalFinal.toLocaleString('es-CL')}
        </p>
      </div>

      <div className="checkout-grid" style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: 48 }}>
        <form noValidate onSubmit={pagar}>
          {/* Paso 1: Contacto */}
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>Contacto</h2>
          <div style={{ marginBottom: 24 }}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              required
              type="email"
              value={cliente.email}
              onChange={e => actualizar('email', e.target.value)}

            />
          </div>

          <div className="separador-suave" style={{ marginBottom: 24 }} />

          {/* Paso 2: Dirección — bloqueado hasta que el contacto sea válido */}
          <fieldset
            disabled={!contactoCompleto}
            style={{ border: 'none', padding: 0, margin: 0, opacity: contactoCompleto ? 1 : 0.4 }}
          >
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>Dirección de envío</h2>

            <div className="grid-2" style={{ marginBottom: 16 }}>
              <div>
                <label htmlFor="nombre">Nombre</label>
                <input
                  id="nombre"
                  required
                  value={cliente.nombre}
                  onChange={e => actualizar('nombre', e.target.value)}

                />
              </div>
              <div>
                <label htmlFor="apellido">Apellido</label>
                <input
                  id="apellido"
                  required
                  value={cliente.apellido}
                  onChange={e => actualizar('apellido', e.target.value)}

                />
              </div>
            </div>

            <div className="grid-2" style={{ marginBottom: 16 }}>
              <div>
                <label htmlFor="region">Región</label>
                <SelectOpciones
                  id="region"
                  options={REGIONES}
                  value={cliente.region}
                  onChange={cambiarRegion}
                  placeholder="Selecciona una región"
                />
              </div>
              <div>
                <label htmlFor="comuna">Comuna</label>
                <SelectOpciones
                  id="comuna"
                  options={COMUNAS_POR_REGION[cliente.region] || []}
                  value={cliente.comuna}
                  onChange={v => actualizar('comuna', v)}
                  disabled={!cliente.region}
                  placeholder="Selecciona una comuna"
                />
                <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '4px 0 0' }}>
                  Asegúrate que la dirección a ingresar pertenezca a la comuna. Evita inconvenientes de entrega.
                </p>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="codigoPostal">Código postal</label>
              <input
                id="codigoPostal"
                required
                value={cliente.codigoPostal}
                onChange={e => actualizar('codigoPostal', e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="direccion">Dirección</label>
              <input
                id="direccion"
                required
                placeholder="Calle"
                value={cliente.direccion}
                onChange={e => actualizar('direccion', e.target.value)}
              />
            </div>

            <div className="grid-2" style={{ marginBottom: 16 }}>
              <div>
                <label htmlFor="numero">Número de calle</label>
                <input
                  id="numero"
                  required
                  value={cliente.numero}
                  onChange={e => actualizar('numero', e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="dpto">Dpto/Block/Piso</label>
                <input
                  id="dpto"
                  value={cliente.dpto}
                  onChange={e => actualizar('dpto', e.target.value)}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="ciudad">Ciudad</label>
              <input
                id="ciudad"
                required
                value={cliente.ciudad}
                onChange={e => actualizar('ciudad', e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label htmlFor="telefono">Teléfono</label>
              <div className="input-prefijo" style={telefonoError ? { borderColor: '#ef4444' } : undefined}>
                <svg
                  aria-hidden="true"
                  width={20}
                  height={14}
                  viewBox="0 0 60 40"
                  style={{ borderRadius: 3, flexShrink: 0 }}
                >
                  <rect width="60" height="20" fill="#FFFFFF" />
                  <rect y="20" width="60" height="20" fill="#D52B1E" />
                  <rect width="20" height="20" fill="#0039A6" />
                  <polygon
                    points="10,3 11.65,7.73 16.66,7.84 12.66,10.87 14.12,15.66 10,12.8 5.89,15.66 7.34,10.87 3.34,7.84 8.35,7.73"
                    fill="#FFFFFF"
                  />
                </svg>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, opacity: .85 }}>+569</span>
                <span style={{ opacity: .4 }}>|</span>
                <input
                  id="telefono"
                  required
                  type="tel"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={8}
                  placeholder="1234 5678"
                  value={cliente.telefono}
                  onChange={e => actualizar('telefono', e.target.value.replace(/\D/g, '').slice(0, 8))}
                />
              </div>
              {telefonoError && <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>{telefonoError}</p>}
              <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '4px 0 0' }}>
                Solo te llamaremos si tenemos alguna duda sobre tu pedido.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, marginTop: 30 }}>
              <input
                id="guardarDatos"
                type="checkbox"
                checked={guardarDatos}
                onChange={e => setGuardarDatos(e.target.checked)}
                style={{ margin: 0, flexShrink: 0, width: 16, height: 16 }}
              />
              <label htmlFor="guardarDatos" style={{ fontSize: 13, margin: 0 }}>
                Guardar la dirección y los datos de contacto para futuros pedidos
              </label>
            </div>
          </fieldset>

          <div className="separador-suave" style={{ marginBottom: 24 }} />

          {/* Paso 3: Datos personales — bloqueado hasta completar la dirección */}
          <fieldset
            disabled={!direccionCompleta}
            style={{ border: 'none', padding: 0, margin: 0, opacity: direccionCompleta ? 1 : 0.4 }}
          >
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>Datos personales</h2>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="tipoDocumento">Tipo de documento</label>
              <SelectOpciones
                id="tipoDocumento"
                options={[{ value: 'boleta', label: 'Boleta' }, { value: 'factura', label: 'Factura' }]}
                value={cliente.tipoDocumento}
                onChange={v => actualizar('tipoDocumento', v)}
                placeholder="Selecciona una opción"
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="tipoIdentificacion">Identificación</label>
              <SelectOpciones
                id="tipoIdentificacion"
                options={[{ value: 'rut', label: 'RUT' }, { value: 'pasaporte', label: 'Pasaporte' }]}
                value={cliente.tipoIdentificacion}
                onChange={v => actualizar('tipoIdentificacion', v)}
                placeholder="Selecciona una opción"
              />
            </div>

            {cliente.tipoIdentificacion && (
              <div style={{ marginBottom: 8 }}>
                <label htmlFor="rut">{cliente.tipoIdentificacion === 'rut' ? 'RUT' : 'Número de pasaporte'}</label>
                <input
                  id="rut"
                  required
                  placeholder={cliente.tipoIdentificacion === 'rut' ? '12345678-K' : ''}
                  value={cliente.rut}
                  onChange={e => actualizar('rut', e.target.value)}
                  style={{
                    borderColor: rutError ? '#ef4444' : undefined,
                  }}
                />
                {rutError && (
                  <p style={{ color: '#ef4444', fontSize: 12, margin: '6px 0 0' }}>
                    {rutError}
                  </p>
                )}
              </div>
            )}

            {cliente.tipoDocumento === 'factura' && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 16 }}>
                  <label htmlFor="razonSocial">Razón social</label>
                  <input
                    id="razonSocial"
                    required
                    value={cliente.razonSocial}
                    onChange={e => actualizar('razonSocial', e.target.value)}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <label htmlFor="giro">Giro</label>
                  <input
                    id="giro"
                    required
                    value={cliente.giro}
                    onChange={e => actualizar('giro', e.target.value)}
                  />
                </div>
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, marginTop: 30 }}>
              <input
                id="mayorEdad"
                type="checkbox"
                required
                checked={mayorEdad}
                onChange={e => setMayorEdad(e.target.checked)}
                style={{ margin: 0, flexShrink: 0, width: 16, height: 16 }}
              />
              <label htmlFor="mayorEdad" style={{ fontSize: 13, margin: 0 }}>
                Soy mayor de 14 años
              </label>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 24 }}>
              <input
                id="aceptaTerminos"
                type="checkbox"
                required
                checked={aceptaTerminos}
                onChange={e => setAceptaTerminos(e.target.checked)}
                style={{ margin: '2px 0 0', flexShrink: 0, width: 16, height: 16 }}
              />
              <label htmlFor="aceptaTerminos" style={{ fontSize: 13, margin: 0, lineHeight: 1.5 }}>
                Acepto los <a href="/terminos" target="_blank" rel="noreferrer">Términos y condiciones</a> y la{' '}
                <a href="/privacidad" target="_blank" rel="noreferrer">Política de privacidad</a>
              </label>
            </div>
          </fieldset>

          <div className="separador-suave" style={{ marginBottom: 24 }} />

          {/* Paso 4: Opciones de entrega — bloqueado hasta completar datos personales */}
          <fieldset
            disabled={!datosPersonalesCompletos}
            style={{ border: 'none', padding: 0, margin: 0, opacity: datosPersonalesCompletos ? 1 : 0.4 }}
          >
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>Opciones de entrega</h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
              <label
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  border: entrega === 'envio' ? '1px solid var(--accent)' : '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  cursor: 'pointer',
                  backgroundColor: 'var(--surface-3)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input
                    type="radio"
                    name="entrega"
                    checked={entrega === 'envio'}
                    onChange={() => setEntrega('envio')}
                    style={{ margin: 0 }}
                  />
                  <div>
                    <p style={{ fontWeight: 600, fontSize: 14, margin: '0 0 2px' }}>Envío estándar</p>
                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>2 a 4 días hábiles</p>
                  </div>
                </div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>
                  {total >= ENVIO_GRATIS_DESDE ? 'Gratis' : `$${COSTO_ENVIO_ESTANDAR.toLocaleString('es-CL')}`}
                </span>
              </label>

              <label
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  border: entrega === 'retiro' ? '1px solid var(--accent)' : '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input
                    type="radio"
                    name="entrega"
                    checked={entrega === 'retiro'}
                    onChange={() => setEntrega('retiro')}
                    style={{ margin: 0 }}
                  />
                  <div>
                    <p style={{ fontWeight: 600, fontSize: 14, margin: '0 0 2px' }}>Retiro en tienda</p>
                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>Disponible en 24 horas</p>
                  </div>
                </div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>Gratis</span>
              </label>
            </div>
          </fieldset>

          {error && (
            <p style={{ color: 'var(--danger, #D8302F)', fontSize: 13, marginBottom: 16 }}>
              {error}
            </p>
          )}

          <button
            className="btn btn-primary"
            disabled={!entregaSeleccionada || enviando}
            type="submit"
            style={{
              opacity: entregaSeleccionada ? 1 : 0.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              color: 'var(--text)'
            }}
          >
            {enviando ? (
              'Redirigiendo…'
            ) : (
              <>
                Pagar con
                <img src={mediaPath('tuu.png')} alt="Tuu" style={{ height: 16, verticalAlign: 'middle' }} />
                →
              </>
            )}
          </button>
        </form>

        <aside
          style={{
            background: 'var(--surface-3)',
            border: '1px solid var(--surface-2)',
            borderRadius: 12,
            padding: 24,
            height: 'fit-content',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline', marginBottom: 2 }}>
            <Link to="/carrito" style={{ fontSize: 13, color: 'var(--surface-2)' }}>Editar</Link>
          </div>

          <img src={mediaPath('apolo-vibes-logo.png')} alt='logo-icon' className='logoicon'></img>
          <img src={mediaPath('nombrelogo.png')} alt='logo' className='nombre-logo'></img>

          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'baseline', marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, margin: 0, color: 'var(--accent)' }}>Tu pedido</h3>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
            <span>{items.length} {items.length === 1 ? 'producto' : 'productos'}</span>
            <span>${total.toLocaleString('es-CL')}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 14 }}>
            <span>Entrega</span>
            <span>{entrega === null ? 'Por definir' : costoEnvio === 0 ? 'Gratis' : `$${costoEnvio.toLocaleString('es-CL')}`}</span>
          </div>

          <div
            className="separador-suave"
            style={{ display: 'flex', flexDirection: 'column', paddingTop: 14, marginBottom: 20 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>Monto neto</span>
              <span>${montoNeto.toLocaleString('es-CL')}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>IVA (19%)</span>
              <span>${montoIva.toLocaleString('es-CL')}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>Total</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>${totalFinal.toLocaleString('es-CL')}</span>
            </div>
          </div>
          <div style={{ borderTop: '1px solid var(--surface-3)', paddingTop: 16, display: 'flex', flexDirection: 'column' }}>
            <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 16px' }}>
              Detalle del pedido
            </p>
            {items.map(item => (
              <div key={item.itemId ?? item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: 8,
                    overflow: 'hidden',
                    background: item.imagen ? '#FFFFFF' : 'var(--surface-2)',
                    flexShrink: 0,
                  }}
                >
                  {item.imagen && (
                    <img
                      src={item.imagen}
                      alt={item.nombre}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  )}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, margin: '0 0 4px', color: 'var(--surface)' }}>{item.nombre} ( {item.cantidad}u )</p>
                  {item.color && (
                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>
                      Color: {item.color}
                    </p>
                  )}
                  <p style={{ fontSize: 13, color: 'var(--text-dim)', flexShrink: 0 }}>
                    ${item.precio.toLocaleString('es-CL')}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  )
}