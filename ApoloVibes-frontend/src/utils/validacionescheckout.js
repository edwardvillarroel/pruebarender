export const OBLIGATORIO = 'Campo obligatorio.'

const RE_NOMBRE = /^\p{L}[\p{L}\s'’.-]{1,59}$/u
const RE_EMPRESA = /^[\p{L}\p{N}\s&.,'’"\-/()+°#:]+$/u

export const normalizarEmpresa = v => v.replace(/[^\p{L}\p{N}\s&.,'’\-/()]/gu, '').slice(0, 100)
export const emailValido = v => v.trim().length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim())
export const nombreValido = v => RE_NOMBRE.test(v.trim())
export const telefonoValido = v => /^\d{8}$/.test(v)
export const codigoPostalValido = v => /^\d{7}$/.test(v)
export const numeroCalleValido = v => /^(\d{1,6}\s?[A-Za-z]?|S\/N)$/i.test(v.trim())
export const pasaporteValido = v => /^[A-Z0-9]{5,20}$/.test(v)

export function rutValido(rutSucio) {
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


export const soloDigitos = (valor, max) => valor.replace(/\D/g, '').slice(0, max)

export function normalizarTelefono(valor) {
  let d = valor.replace(/\D/g, '')
  if (d.length > 8) d = d.replace(/^(?:56)?9/, '')
  return d.slice(0, 8)
}

export function normalizarRut(valor) {
  const limpio = valor.replace(/[^0-9kK]/g, '').toUpperCase().slice(0, 9)
  return limpio.length > 1 ? `${limpio.slice(0, -1)}-${limpio.slice(-1)}` : limpio
}

export const normalizarPasaporte = valor => valor.replace(/[^0-9a-zA-Z]/g, '').toUpperCase().slice(0, 20)

export const normalizarIdentificacion = (tipo, valor) =>
  tipo === 'rut' ? normalizarRut(valor) : normalizarPasaporte(valor)


export function hoyISO() {
  const h = new Date()
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, '0')}-${String(h.getDate()).padStart(2, '0')}`
}

export function edadDesde(fechaISO) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fechaISO)) return null
  const [a, m, d] = fechaISO.split('-').map(Number)
  const fecha = new Date(a, m - 1, d)
  if (fecha.getFullYear() !== a || fecha.getMonth() !== m - 1 || fecha.getDate() !== d) return null

  const hoy = new Date()
  let edad = hoy.getFullYear() - a
  const yaCumplio = hoy.getMonth() > m - 1 || (hoy.getMonth() === m - 1 && hoy.getDate() >= d)
  if (!yaCumplio) edad--
  return edad
}

export const esMayorDeEdad = edad => edad !== null && edad >= 18 && edad <= 120

function texto(valor, esValido, mensaje) {
  const v = valor.trim()
  if (!v) return OBLIGATORIO
  return esValido(v) ? '' : mensaje
}

function errorIdentificacion(tipo, valor) {
  if (!tipo) return ''
  if (!valor) return OBLIGATORIO
  if (tipo === 'pasaporte') {
    return pasaporteValido(valor) ? '' : 'El pasaporte debe tener entre 5 y 20 letras o números.'
  }
  if (!/^\d{7,8}-[0-9K]$/.test(valor)) return 'Formato inválido. Ejemplo: 12345678-5'
  return rutValido(valor) ? '' : 'El dígito verificador no es válido. Revisa el RUT ingresado.'
}

export function calcularErrores(c, fechaNacimiento, aceptaTerminos) {
  const esFactura = c.tipoDocumento === 'factura'
  const edad = edadDesde(fechaNacimiento)
  const errorNombre = 'Usa solo letras (entre 2 y 60 caracteres).'
  const errorEmpresa = 'Ingresa entre 2 y 100 caracteres.'
  const largoEmpresa = v => v.length >= 2 && v.length <= 100 && RE_EMPRESA.test(v)

  return {
    email: texto(c.email, emailValido, 'Ingresa un email válido, por ejemplo nombre@correo.cl.'),
    nombre: texto(c.nombre, nombreValido, errorNombre),
    apellido: texto(c.apellido, nombreValido, errorNombre),
    region: c.region ? '' : OBLIGATORIO,
    comuna: c.comuna ? '' : OBLIGATORIO,
    codigoPostal: texto(c.codigoPostal, codigoPostalValido, 'El código postal tiene 7 dígitos.'),
    direccion: texto(c.direccion, v => v.length >= 3 && v.length <= 100, 'Ingresa el nombre de la calle (entre 3 y 100 caracteres).'),
    numero: texto(c.numero, numeroCalleValido, 'Ingresa el número de la calle, o S/N si no tiene.'),
    ciudad: texto(c.ciudad, nombreValido, errorNombre),
    telefono: !c.telefono
      ? OBLIGATORIO
      : telefonoValido(c.telefono) ? '' : 'Ingresa los 8 dígitos de tu móvil, por ejemplo 1234 5678.',
    tipoDocumento: c.tipoDocumento ? '' : OBLIGATORIO,
    tipoIdentificacion: !c.tipoIdentificacion ? OBLIGATORIO : esFactura && c.tipoIdentificacion !== 'rut' ? 'Para facturas debes usar RUT.' : '',
    rut: errorIdentificacion(c.tipoIdentificacion, c.rut),
    razonSocial: esFactura ? texto(c.razonSocial, largoEmpresa, errorEmpresa) : '',
    giro: esFactura ? texto(c.giro, largoEmpresa, errorEmpresa) : '',
    fechaNacimiento: !fechaNacimiento
      ? OBLIGATORIO
      : edad === null || edad < 0 || edad > 120
        ? 'Ingresa una fecha de nacimiento válida.'
        : edad < 18 ? 'Debes ser mayor de 18 años para comprar en esta tienda.' : '',
    aceptaTerminos: aceptaTerminos ? '' : 'Debes aceptar los términos y la política de privacidad.',
  }
}

export function datosDesdeUsuario(user) {
  if (!user) return {}
  let nombre = (user.nombre ?? user.name ?? user.given_name ?? '').trim()
  let apellido = (user.apellido ?? user.family_name ?? '').trim()

  if (nombre && !apellido && nombre.includes(' ')) {
    const partes = nombre.split(/\s+/)
    const nApellidos = partes.length >= 3 ? 2 : 1
    apellido = partes.slice(-nApellidos).join(' ')
    nombre = partes.slice(0, -nApellidos).join(' ')
  }
  return {
    email: (user.email ?? user.correo ?? '').trim(),
    nombre,
    apellido,
    telefono: normalizarTelefono(user.telefono ?? ''),
  }
}

export function clienteParaEnvio(c) {
  const limpio = Object.fromEntries(
    Object.entries(c).map(([k, v]) => [k, typeof v === 'string' ? v.trim() : v]),
  )
  const esFactura = limpio.tipoDocumento === 'factura'
  return {
    ...limpio,
    telefono: '+569' + limpio.telefono,
    razonSocial: esFactura ? limpio.razonSocial : '',
    giro: esFactura ? limpio.giro : '',
  }
}