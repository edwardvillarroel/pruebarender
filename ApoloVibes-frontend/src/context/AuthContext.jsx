import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../services/api.js'

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

  useEffect(() => {
    if (auth) {
      localStorage.setItem(AUTH_KEY, JSON.stringify(auth))
    } else {
      localStorage.removeItem(AUTH_KEY)
    }
  }, [auth])

  const user = auth?.user ?? null

  const login = useCallback((sesion) => setAuth(sesion), [])

  function actualizarUsuario(nuevoUser) {
    setAuth(prev => (prev ? { ...prev, user: nuevoUser } : prev))
  }

  function logout() {
    api.logout()
    setAuth(null)
  }

  // Callback de Google OAuth: el gateway redirige aquí con ?login=google.
  // Al volver del navegador, completa la sesión vía /auth/refresh (el hook
  // httpOnly `refresh_token` ya quedó seteado por el gateway).
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
      alert(mensaje)
      return
    }
    if (params.get('mfa')) {
      // MFA pendiente: se abre el modal en modo MFA (ver LoginModal).
      sessionStorage.setItem('apolovibes_mfa_pendiente', '1')
      window.dispatchEvent(new CustomEvent('apolovibes:google-mfa'))
      return
    }
    ;(async () => {
      try {
        const data = await api.post('/auth/refresh', {})
        setAuth({ token: data.access_token, user: data.user })
      } catch {
        alert('No se pudo iniciar sesión con Google')
      }
    })()
  }, [])

  return (
    <AuthContext.Provider value={{ user, token: auth?.token ?? null, isLoggedIn: !!user, isAdmin: user?.rol === 'admin', login, logout, actualizarUsuario }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
