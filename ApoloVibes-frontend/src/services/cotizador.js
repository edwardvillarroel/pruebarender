import { apiCotizador } from './api.js'

// Firma canonica de las especificaciones de la pieza. Debe coincidir con la
// que calcula el backend (`_firma_especificaciones` en CrearSolicitudDiseno) para
// decidir si una estimacion calculada por el cliente se puede reutilizar.
function numeroFirma(valor, defecto = '10') {
  const texto = valor === null || valor === undefined ? '' : String(valor).trim()
  if (texto === '') return defecto
  const numero = Number(texto.replace(',', '.'))
  if (!Number.isFinite(numero)) return texto
  const entero = Number.isInteger(numero)
  return String(numero)
}

export function firmaEspecificaciones(form) {
  const colorFinal = form.color === 'Otro' ? form.colorOtro : form.color
  const partes = [
    numeroFirma(form.alto),
    numeroFirma(form.ancho),
    numeroFirma(form.largo),
    (form.unidad || 'cm').trim() || 'cm',
    String(Number(form.cantidad) > 0 ? Number(form.cantidad) : 1),
    (form.uso || 'Decorativo').trim() || 'Decorativo',
    String((form.material || '').trim()),
    (colorFinal || 'Negro').trim() || 'Negro',
  ]
  return partes.join('|')
}

export async function estimarPieza(archivo, form) {
  const fd = new FormData()
  fd.append('imagen', archivo)
  fd.append('alto', form.alto)
  fd.append('ancho', form.ancho)
  fd.append('largo', form.largo)
  fd.append('unidad', form.unidad)
  fd.append('cantidad', form.cantidad)
  fd.append('uso', form.uso)
  fd.append('material_usuario', form.material)
  fd.append('color', form.color === 'Otro' ? form.colorOtro : form.color)

  const resultado = await apiCotizador.estimar(fd)
  return { ...resultado, firma: firmaEspecificaciones(form) }
}
