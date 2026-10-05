import { useState, useEffect, useRef } from 'react'
import { mediaPath } from '../utils/media.js'
import { Navigate, Link } from 'react-router-dom'
import { useCart } from '../context/CartContext.jsx'
import { iniciarPago } from '../services/payment.js'
import SelectOpciones from '../components/SelectOpciones.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { REGIONES, COMUNAS_POR_REGION } from '../services/regiones.js'
import { calcularErrores, clienteParaEnvio, datosDesdeUsuario, edadDesde, esMayorDeEdad,
   hoyISO, normalizarEmpresa, normalizarIdentificacion, normalizarTelefono, soloDigitos,} from '../utils/validacionescheckout.js'


const ENVIO_GRATIS_DESDE = 50000
const clp = n => `$${n.toLocaleString('es-CL')}`

const tituloSeccion = { fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }
const estiloAyuda = { fontSize: 12, color: 'var(--text-dim)', margin: '4px 0 0' }
const estiloError = { color: '#ef4444', fontSize: 12, margin: '6px 0 0' }
const sinBorde = { border: 'none', padding: 0, margin: 0 }

const CLIENTE_INICIAL = {
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
}

const OPCIONES_ENTREGA = [
  { valor: 'envio', titulo: 'Envío estándar', detalle: 'Plazos y costo según la empresa de transporte'},
  { valor: 'retiro', titulo: 'Retiro', detalle: 'Disponible en 24 horas en Álvarez 1106, Viña del Mar'},
]

function Campo({ id, label, error, ayuda, style, children }){
  return (
    <div style={{ marginBottom: 16, ...style }} >
      <label htmlFor={id}>{label}</label>
      {children}
      {error && <p id={`${id}-error`} role="alert" style={estiloError}>{error}</p>}
      {ayuda && <p style={estiloAyuda}>{ayuda}</p>}
    </div>
  )
}

export default function Checkout() {
  const { items, total } = useCart()
  const { user } = useAuth()
  const claveRef  = useRef(null)
  const enviandoRef = useRef(false)
  if (claveRef.current === null) claveRef.current = crypto.randomUUID()

  const [cliente, setCliente] = useState(CLIENTE_INICIAL)
  const [fechaNacimiento, setFechaNacimiento] = useState('')
  const [guardarDatos, setGuardarDatos] = useState(false)
  const [aceptaTerminos, setAceptaTerminos] = useState(false)
  const [entrega, setEntrega] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [tocado, setTocado] = useState({})

    useEffect(() => {
    const d =  datosDesdeUsuario(user)
    setCliente(prev => ({
      ...prev,
      email: d.email || prev.email,
      nombre: prev.nombre || d.nombre || '',
      apellido: prev.apellido || d.apellido || '',
      telefono: prev.telefono || d.telefono || '',
    }))
  }, [user])

  if (!user) return <Navigate to="/" replace />
  if (items.length === 0) {
    return <Navigate to="/carrito" replace />
  }
  const emailDeCuenta = !!(user?.email ?? user?.correo)

  // validaciones
  const errores = calcularErrores(cliente, fechaNacimiento, aceptaTerminos)
  const edad = edadDesde(fechaNacimiento)
  const esMayor = esMayorDeEdad(edad)
  const errorDe = campo => (tocado[campo] ? errores[campo] : '')
  const borde = campo => (errorDe(campo) ? { borderColor: '#ef4444' } : undefined)
  const sinErrores = campos => campos.every(c => !errores[c])
  const marcar = campo => setTocado(prev => (prev[campo] ? prev : {...prev, [campo]: true }))

  const contactoCompleto = sinErrores(['email'])
  const direccionCompleta = contactoCompleto && sinErrores(['nombre', 'apellido', 'region', 'comuna', 'codigoPostal', 'direccion', 'numero', 'ciudad', 'telefono'])
  const datosPersonalesCompletos = direccionCompleta && sinErrores(['tipoDocumento', 'tipoIdentificacion', 'rut', 'razonSocial', 'giro', 'fechaNacimiento', 'aceptaTerminos'])
  const entregaSeleccionada = datosPersonalesCompletos && entrega !== null

  //totales
  const envioGratis = total >= ENVIO_GRATIS_DESDE
  const etiquetaEnvio = tipo => (tipo === 'retiro' || envioGratis ? 'Gratis' : 'Por pagar')
  const totalFinal = total
  const montoNeto = Math.round(totalFinal / 1.19)
  const montoIva = totalFinal - montoNeto

  //handles
  function actualizar(campo, valor) {
    setCliente(prev => ({ ...prev, [campo]: valor }))
  }

  function cambiarRegion(valor) {
    setCliente(prev => ({ ...prev, region: valor, comuna: '' }))
  }

  function cambiarTipoIdentificacion(valor) {
    setCliente(prev => ({ ...prev, tipoIdentificacion: valor, rut: ''}))
    setTocado(prev => ({ ...prev, rut: false}))
  }

  function cambiarTipoDocumento(valor){
    setCliente(prev => ({
      ...prev,
      tipoDocumento: valor,
      ...(valor === 'factura' && prev.tipoIdentificacion === 'pasaporte' ? { tipoIdentificacion: 'rut', rut: ''} : {}),
    }))
    setTocado(prev => ({...prev, rut: false}))
  }

  //prop
  function campo (nombre, normalizar){
    const hayError = !!errorDe(nombre)
    return {
      id: nombre,
      value: cliente[nombre],
      onChange: e => actualizar(nombre, normalizar ? normalizar(e.target.value) : e.target.value),
      onBlur: () => {
        marcar(nombre)
        const recortado = cliente[nombre].trim()
        if (recortado !== cliente[nombre]) actualizar(nombre, recortado)
      },
    'aria-invalid': hayError || undefined,
      'aria-describedby': hayError ? `${nombre}-error` : undefined,
    }
  }

  async function pagar(e) {
    e.preventDefault()
    setError(null)
    if (!entregaSeleccionada || enviandoRef.current) return
    
    enviandoRef.current = true
    setEnviando(true)
    try {
      await iniciarPago({ 
        items, 
        cliente: clienteParaEnvio(cliente),
        entrega,
        totalEsperado: totalFinal,
        claveIdempotencia: claveRef.current,
        guardarDatos,
      mayorEdad: esMayor, 
      aceptaTerminos,
    })
    } catch (err) {
      setError(err.message || 'No pudimos iniciar el pago. Intenta nuevamente.')
      enviandoRef.current = false
      setEnviando(false)
    }
  }

  const esFactura = cliente.tipoDocumento === 'factura'
  const esRut = cliente.tipoIdentificacion === 'rut'


  return (
    <section className="wrap" style={{ paddingTop: '48px', paddingBottom: '80px' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <img src={mediaPath('nombrelogo.png')} alt='logo' className='nombre-logo'></img>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
          ({items.length} {items.length === 1 ? 'producto' : 'productos'}) &nbsp; 
        </p>
      </div>

      <div className="checkout-grid" style={{ display: 'grid', gridTemplateColumns: '1.2fr .8fr', gap: 48 }}>
        <form className="checkout-form" noValidate onSubmit={pagar}>
          {/* Paso 1: Contacto */}
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16, color: 'var(--surface)' }}>Contacto</h2>
          <Campo
          id="email"
          label="Email"
          error={errorDe('email')}
          ayuda={emailDeCuenta ? 'Este es el email de tu cuenta. Aquí te enviaremos la confirmación del pedido.' : undefined}
          style={{ margintBottom: 24 }}  
          >
            <input
            {...campo('email')}
              required
              type="email"
              autoComplete="email"
              maxLength={120}
              readOnly={emailDeCuenta}
              style={emailDeCuenta ? { opacity: 0.7, cursor: 'not-allowed'} : borde('email')}
            />
          </Campo>

          <div className="separador-suave" style={{ marginBottom: 24 }} />

          {/* Paso 2: Dirección — bloqueado hasta que el contacto sea válido */}
          <fieldset
            disabled={!contactoCompleto}
            style={{ ...sinBorde, opacity: contactoCompleto ? 1 : 0.4 }}
          >
            <h2 style={tituloSeccion}>Dirección de envío</h2>

            <div className="grid-2" style={{ marginBottom: 16 }}>
              <Campo
              id="nombre"
              label="Nombre"
              error={errorDe('nombre')}
              style={{ marginBottom: 0}}>
                <input
                {...campo('nombre')}
                required
                autoComplete="given-name"
                maxLength={60}
                style={borde('nombre')}/>
              </Campo>
              <Campo
              id="apellido"
              label="Apellido"
              error={errorDe('apellido')}
              style={{ marginBottom: 0}}>
                <input
                {...campo('apellido')}
                required
                autoComplete="family-name"
                maxLength={60}
              style={borde('apellido')}/>
              </Campo>
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

             <Campo id="codigoPostal" label="Código postal" error={errorDe('codigoPostal')} ayuda="7 dígitos.">
                <input
                {...campo('codigoPostal', v => soloDigitos(v, 7))}
                required
                inputMode='numeric'
                autoComplete="postal-code"
                maxLength={7}
              style={borde('codigoPostal')}/>
              </Campo>

            <Campo id="direccion" label="Dirección" error={errorDe('direccion')}>
                <input
                {...campo('direccion')}
                required
                placeholder="Calle"
                autoComplete="address-line1"
                maxLength={100}
              style={borde('direccion')}/>
              </Campo>


            <div className="grid-2" style={{ marginBottom: 16 }}>
             <Campo id="numero" label="Número de calle" error={errorDe('numero')} style={{ marginBottom: 0 }}>
                <input
                {...campo('numero')}
                required
                autoComplete="off"
                maxLength={10}
              style={borde('numero')}/>
              </Campo>
              <Campo id="dpto" label="Dpto/Block/Piso" style={{ marginBottom: 0 }}>
                <input
                {...campo('dpto')}
                autoComplete="address-line2"
                maxLength={30}/>
              </Campo>
            </div>

             <Campo id="ciudad" label="Ciudad" error={errorDe('ciudad')}>
                <input
                {...campo('ciudad')}
                required
                autoComplete="address-level2"
                maxLength={60}
                style={borde('ciudad')}/>
              </Campo>

            <Campo
              id="telefono"
              label="Teléfono"
              error={errorDe('telefono')}
              ayuda="Solo te llamaremos si tenemos alguna duda sobre tu pedido."
              style={{ marginBottom: 12 }}
            >
              <div className="input-prefijo" style={borde('telefono')}>
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
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, opacity: 0.85 }}>+569</span>
                <span style={{ opacity: 0.4 }}>|</span>
                <input
                  {...campo('telefono', normalizarTelefono)}
                  required
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  placeholder="1234 5678"
                />
              </div>
            </Campo>

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
            style={{ ...sinBorde, opacity: direccionCompleta ? 1 : 0.4 }}
          >
            <h2 style={tituloSeccion}>Datos personales</h2>

             <Campo id="tipoDocumento" label="Tipo de documento">
              <SelectOpciones
                id="tipoDocumento"
                options={[{ value: 'boleta', label: 'Boleta' }, { value: 'factura', label: 'Factura' }]}
                value={cliente.tipoDocumento}
                onChange={cambiarTipoDocumento}
                placeholder="Selecciona una opción"
              />
            </Campo>

             <Campo id="tipoIdentificacion" label="Identificación">
              <SelectOpciones
                id="tipoIdentificacion"
                options={esFactura ? [{ value: 'rut', label: 'RUT' }] : [{ value: 'rut', label: 'RUT'}, { value: 'pasaporte', label: 'Pasaporte' }]}
                value={cliente.tipoIdentificacion}
                onChange={cambiarTipoIdentificacion}
                placeholder="Selecciona una opción"
              />
            </Campo>

            {cliente.tipoIdentificacion && (
              <Campo
                id="rut"
                label={esRut ? (esFactura ? 'RUT empresa' : 'RUT') : 'Número de pasaporte'}
                error={errorDe('rut')}
                ayuda={esRut ? 'Escríbelo sin puntos; el guión se agrega solo.' : undefined}
                style={{ marginBottom: 8 }}
              >
                <input
                  {...campo('rut', v => normalizarIdentificacion(cliente.tipoIdentificacion, v))}
                  required
                  autoComplete="off"
                  maxLength={esRut ? 10 : 20}
                  placeholder={esRut ? '12345678-5' : ''}
                  style={borde('rut')}
                />
              </Campo>
            )}

            {esFactura && (
              <div style={{ marginTop: 16 }}>
                <Campo id="razonSocial" label="Razón social" error={errorDe('razonSocial')}>
                  <input {...campo('razonSocial', normalizarEmpresa)} required maxLength={100} style={borde('razonSocial')} />
                </Campo>
                <Campo id="giro" label="Giro" error={errorDe('giro')}>
                  <input {...campo('giro', normalizarEmpresa)} required maxLength={100} style={borde('giro')} />
                </Campo>
              </div>
            )}

            <Campo
            id="fechaNacimiento"
            label="Fecha de nacimiento"
            error={errorDe('fechaNacimiento')}
            ayuda="Solo la usamos para comprobar que eres mayor de edad; no la guardamos."
            style={{ marginTop: 30, marginBottom: 20}}
            >
              <input 
              id="fechaNacimiento"
              type="date"
              required
              max={hoyISO()}
              autoComplete="bday"
              value={fechaNacimiento}
              onChange={e => setFechaNacimiento(e.target.value)}
              onBlur={() => marcar('fechaNacimiento')}
              aria-invalid={errorDe('fechaNacimiento') ? true : undefined}
              aria-describedby={errorDe('fechaNacimiento') ? 'fechaNacimiento-error' : undefined}
              style={borde('fechaNacimiento')}
              />       
            </Campo>

            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <input
                  id="aceptaTerminos"
                  type="checkbox"
                  required
                  checked={aceptaTerminos}
                  onChange={e => { setAceptaTerminos(e.target.checked); marcar('aceptaTerminos') }}
                  onBlur={() => marcar('aceptaTerminos')}
                  aria-invalid={errorDe('aceptaTerminos') ? true : undefined}
                  aria-describedby={errorDe('aceptaTerminos') ? 'aceptaTerminos-error' : undefined}
                  style={{ margin: '2px 0 0', flexShrink: 0, width: 16, height: 16 }}
                />
                <label htmlFor="aceptaTerminos" style={{ fontSize: 13, margin: 0, lineHeight: 1.5 }}>
                  Acepto los <a href="/terminos" target="_blank" rel="noreferrer">Términos y condiciones</a> y la{' '}
                  <a href="/privacidad" target="_blank" rel="noreferrer">Política de privacidad</a>
                </label>
              </div>
              {errorDe('aceptaTerminos') && (
                <p id="aceptaTerminos-error" role="alert" style={estiloError}>{errorDe('aceptaTerminos')}</p>
              )}
            </div>
          </fieldset>

          <div className="separador-suave" style={{ marginBottom: 24 }} />
        {/* Paso 4: Opciones de entrega — bloqueado hasta completar datos personales */}
          <fieldset
            disabled={!datosPersonalesCompletos}
            style={{ ...sinBorde, opacity: datosPersonalesCompletos ? 1 : 0.4 }}
          >
            <h2 style={tituloSeccion}>Opciones de entrega</h2>
            {!envioGratis && (
              <p style={{ ...estiloAyuda, margin: '0 0 12px' }}>
                Envío gratis en compras desde {clp(ENVIO_GRATIS_DESDE)}. Te faltan {clp(ENVIO_GRATIS_DESDE - total)}.
              </p>
            )}
 
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
              {OPCIONES_ENTREGA.map(op => {
                const activa = entrega === op.valor
                return (
                  <label
                    key={op.valor}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      border: activa ? '1px solid var(--green)' : '1px solid var(--line)',
                      borderRadius: 8,
                      padding: '12px 14px',
                      cursor: 'pointer',
                      backgroundColor: activa ? 'var(--surface-3)' : '#fff',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <input
                        type="radio"
                        name="entrega"
                        checked={activa}
                        onChange={() => setEntrega(op.valor)}
                        style={{ margin: 0, padding: 0, width: 18, height: 18, flexShrink: 0 }}
                      />
                      <div>
                        <p style={{ fontWeight: 600, fontSize: 14, margin: '0 0 2px', color: activa ? 'var(--surface)' : 'var(--text-dim)' }}>
                          {op.titulo}
                        </p>
                        <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: 0 }}>{op.detalle}</p>
                      </div>
                    </div>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: 14,
                        color: activa ? (op.valor === 'retiro' ? 'var(--green)' : 'var(--surface)') : 'var(--text-dim)',
                      }}
                    >
                      {etiquetaEnvio(op.valor)}
                    </span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          {error && (
            <p role="alert" style={{ color: 'var(--danger, #D8302F)', fontSize: 13, marginBottom: 16 }}>
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
            {enviando ? 'Redirigiendo a' : 'Pagar con'}
              <img src={mediaPath('tuu.png')} alt="Tuu" style={{ height: 16, verticalAlign: 'middle' }} />
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
            <span>{clp(total)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 14 }}>
            <span>Entrega</span>
            <span>{entrega === null ? 'Por definir' : etiquetaEnvio(entrega)}</span>
          </div>

          <div
            className="separador-suave"
            style={{ display: 'flex', flexDirection: 'column', paddingTop: 14, marginBottom: 20 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>Monto neto</span>
              <span>{clp(montoNeto)}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-dim)', marginBottom: 8 }}>
              <span>IVA (19%)</span>
              <span>{clp(montoIva)}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>Total</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--surface)' }}>{clp(totalFinal)}</span>
            </div>

            {entrega === 'envio' && !envioGratis && (
              <p style={{ ...estiloAyuda }}>
                El costo del envío no está incluido y se paga a la empresa de transporte.
              </p>
            )}
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