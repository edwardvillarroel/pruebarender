import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function RutaNoAdmin({ children }) {
  const { isAdmin } = useAuth()

  if (isAdmin) {
    return <Navigate to="/admin" replace />
  }

  return children
}
