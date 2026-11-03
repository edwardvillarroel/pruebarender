import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api, intentarRefresh, EVENTO_SESION_EXPIRADA } from '../services/api.js'
import { olvidarAvisoMfa } from '../utils/avisoMfa.js'

const AUTH_KEY = 'apolovibes_auth'

function loadAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadAuth)
  const [cargando, setCargando] = useState(
    () => new URLSearchParams(window.location.search).get('login') === 'google'
  )

  useEffect(() => {
    if (auth) {
      localStorage.setItem(AUTH_KEY, JSON.stringify(auth))
    } else {
      localStorage.removeItem(AUTH_KEY)
    }
  }, [auth])

  const user = auth?.user ?? null

  useEffect(() => {
    const cerrarSesion = () => setAuth(null)
    window.addEventListener(EVENTO_SESION_EXPIRADA, cerrarSesion)
    return () => window.removeEventListener(EVENTO_SESION_EXPIRADA, cerrarSesion)
  }, [])

  const login = useCallback((sesion) => {
    olvidarAvisoMfa(sesion?.user?.id)
    setAuth(sesion)
  }, [])

  function actualizarUsuario(nuevoUser) {
    setAuth(prev => (prev ? { ...prev, user: nuevoUser } : prev))
  }

  async function logout() {
    await api.logout()
    setAuth(null)
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('login') !== 'google') return
    const error = params.get('error')
    const url = new URL(window.location.href)
    url.search = ''
    window.history.replaceState({}, '', url)
    if (error) {
      const mensaje =
        error === 'cuenta_inactiva'
          ? 'Tu cuenta está desactivada'
          : 'No se pudo iniciar sesión con Google'
      setCargando(false)
      alert(mensaje)
      return
    }
    if (params.get('mfa')) {
      setCargando(false)
      sessionStorage.setItem('apolovibes_mfa_pendiente', '1')
      window.dispatchEvent(new CustomEvent('apolovibes:google-mfa'))
      return
    }
    ;(async () => {
      try {
        const { ok, body } = await intentarRefresh()
        if (!ok || !body?.access_token) throw new Error('refresh fallido')
        login({ token: body.access_token, user: body.user })
      } catch {
        alert('No se pudo iniciar sesión con Google')
      } finally {
        setCargando(false)
      }
    })()
  }, [])

  return (
    <AuthContext.Provider value={{ user, token: auth?.token ?? null, isLoggedIn: !!user, isAdmin: user?.rol === 'admin', cargando, login, logout, actualizarUsuario }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
