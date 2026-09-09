import { createContext, useContext, useState, useEffect } from 'react'

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

  function login(sesion) {
    setAuth(sesion)
  }

  function logout() {
    setAuth(null)
  }

  return (
    <AuthContext.Provider value={{ user, token: auth?.token ?? null, isLoggedIn: !!user, isAdmin: user?.rol === 'admin', login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
