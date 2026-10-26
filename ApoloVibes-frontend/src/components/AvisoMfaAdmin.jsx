import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import AvisoMfaModal from './AvisoMfaModal.jsx'
import SeguridadModal from './SeguridadModal.jsx'
import { api } from '../services/api.js'
import { claveAvisoMfa } from '../utils/avisoMfa.js'

export default function AvisoMfaAdmin() {
  const { user, actualizarUsuario } = useAuth()
  const [aviso, setAviso] = useState(false)
  const [seguridad, setSeguridad] = useState(false)

  const clave = user?.id ? claveAvisoMfa(user.id) : null

  useEffect(() => {
    if (!user || user.rol !== 'admin' || user.mfa_activo) return
    if (!clave) return
    if (sessionStorage.getItem(clave)) return
    setAviso(true)
  }, [user?.id, user?.rol, user?.mfa_activo])

  function cerrarAviso() {
    if (clave) sessionStorage.setItem(clave, '1')
    setAviso(false)
  }

  function irAActivar() {
    setAviso(false)
    setSeguridad(true)
  }

  async function cerrarSeguridad() {
    setSeguridad(false)
    try {
      const data = await api.get('/auth/me')
      if (data?.user) {
        actualizarUsuario(data.user)
        if (data.user.mfa_activo && clave) sessionStorage.removeItem(clave)
      }
    } catch {
    }
  }

  if (!user || user.rol !== 'admin' || user.mfa_activo) return null

  return (
    <>
      {aviso && <AvisoMfaModal onActivar={irAActivar} onCerrar={cerrarAviso} />}
      {seguridad && <SeguridadModal onClose={cerrarSeguridad} />}
    </>
  )
}
