import { api } from './api.js'

const POLL_INTERVAL = 2000 // 2 segundos entre consultas
const MAX_ATTEMPTS = 90 // máximo 3 minutos de espera

export async function generarModelo3D(imagen, onProgress) {
  // Paso 1: Subir imagen y crear tarea
  onProgress?.({ status: 'uploading', percent: 5, message: 'Subiendo imagen...' })

  const formData = new FormData()
  formData.append('imagen', imagen)

  const { taskId } = await api.post('/ai/image-to-3d', formData)

  // Paso 2: Polling hasta que el modelo esté listo
  let attempts = 0

  while (attempts < MAX_ATTEMPTS) {
    await new Promise(r => setTimeout(r, POLL_INTERVAL))
    attempts++

    const result = await api.get(`/ai/image-to-3d/${taskId}`)

    switch (result.status) {
      case 'processing':
        onProgress?.({
          status: 'processing',
          percent: Math.min(10 + (attempts / MAX_ATTEMPTS) * 80, 90),
          message: 'Generando modelo 3D con IA...',
        })
        break

      case 'completed':
        onProgress?.({ status: 'completed', percent: 100, message: '¡Modelo listo!' })
        return { modelUrl: result.modelUrl, format: result.format || 'glb' }

      case 'failed':
        throw new Error(result.error || 'La generación del modelo falló.')

      default:
        break
    }
  }

  throw new Error('Tiempo de espera agotado para la generación del modelo.')
}


export function generarModelo3DMock(imagen, onProgress) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const totalDuration = 6000 // 6 segundos simulados

    const interval = setInterval(() => {
      elapsed += 500
      const percent = Math.min((elapsed / totalDuration) * 100, 100)

      if (elapsed < 1000) {
        onProgress?.({ status: 'uploading', percent: 5, message: 'Subiendo imagen...' })
      } else if (elapsed < 2000) {
        onProgress?.({ status: 'processing', percent: 15, message: 'Analizando imagen con IA...' })
      } else if (elapsed < 4000) {
        onProgress?.({ status: 'processing', percent: 40, message: 'Generando geometría 3D...' })
      } else if (elapsed < 5500) {
        onProgress?.({ status: 'processing', percent: 75, message: 'Aplicando texturas y materiales...' })
      } else {
        clearInterval(interval)
        onProgress?.({ status: 'completed', percent: 100, message: '¡Modelo listo!' })

        // Usar un modelo GLB de prueba de drei examples
        resolve({
          modelUrl: 'https://vazxmixjsiawhamofees.supabase.co/storage/v1/object/public/models/gltf/robot-playground/robot-playground.glb',
          format: 'glb',
        })
      }
    }, 500)

    // Si el usuario cancela, limpiar
    return () => {
      clearInterval(interval)
      reject(new Error('Generación cancelada'))
    }
  })
}
