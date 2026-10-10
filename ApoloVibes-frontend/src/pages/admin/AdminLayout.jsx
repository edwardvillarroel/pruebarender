import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { Menu, LogOut, LayoutDashboard, ClipboardList, Package, FileText, ShoppingCart, User } from 'lucide-react'
import ConfirmModal from '../../components/ConfirmModal.jsx'

const navItems = [
  { to: '/admin', end: true, label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/pedidos', label: 'Pedidos', icon: ClipboardList },
  { to: '/admin/inventario', label: 'Inventario', icon: Package },
  { to: '/admin/cotizaciones', label: 'Cotizaciones', icon: FileText },
  { to: '/admin/venta', label: 'Registrar Venta', icon: ShoppingCart },
  { to: '/admin/reportes', label: 'Reporte Ventas', icon: FileText },
]

const itemStyle = ({ isActive }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '10px 12px',
  borderRadius: 8,
  fontSize: 13,
  marginBottom: 2,
  color: isActive ? 'var(--surface)' : 'var(--text)',
  background: isActive ? 'var(--surface-3)' : 'transparent',
  fontWeight: isActive ? 600 : 400,
  textDecoration: 'none',
  transition: 'background .15s, color .15s'
})

const sidebarBtnStyle = {
  display: 'flex', alignItems: 'center', gap: 10, width: '100%',
  padding: '10px 12px', borderRadius: 12, fontSize: 13,
  color: 'var(--red)', background: 'var(--surface-3)', border: 'none',
  textAlign: 'left', cursor: 'pointer', fontWeight: 500,
}

function SidebarContent({ onLogout, user }) {
  const nombreCompleto = [user?.nombre, user?.apellido].filter(Boolean).join(' ') || user?.email || 'Mi cuenta'
  const rolLabel = user?.rol === 'admin' ? 'Admin' : user?.rol || ''

  return (
    <>
      <Link
        to="/"
        style={{
          fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, padding: '6px 10px 28px',
          display: 'block', color: 'inherit', textDecoration: 'none', cursor: 'pointer',
        }}>
        Apolo Vibes 3D
      </Link>
      <nav style={{ flex: 1 }}>
        {navItems.map(({ to, end, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={end} style={itemStyle}>
            <Icon size={16} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.18)',
        marginTop: 12,
        paddingTop: 14,
      }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 12px 12px' }}>
          <div style={{
            width: 34, height: 34, borderRadius: '50%',
            background: user?.foto ? 'transparent' : '#28c72242',
            display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexShrink: 0,
            border: user?.foto ? 'none' : '1px solid var(--green)',
            overflow: 'hidden',
          }}
          >
            {user?.foto ? (
              <img
                src={user.foto}
                alt={nombreCompleto}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <User size={16} style={{ color: 'var(--green)' }} />
            )}
          </div>
          <div style={{ lineHeight: 1.25, overflow: 'hidden' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {nombreCompleto}
            </div>
            {rolLabel && (
              <div style={{ fontSize: 11.5, color: 'var(--surface)' }}>
                {rolLabel}
              </div>
            )}
          </div>
        </div>
      </div>
      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.18)',
        marginTop: 12,
        paddingTop: 14,
      }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 12px 12px' }}>
          <button style={sidebarBtnStyle} onClick={onLogout}>
            <LogOut size={16} />
            Cerrar sesión
          </button>
        </div>
      </div>
    </>
  )
}

export default function AdminLayout() {
  const [showConfirm, setShowConfirm] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      setShowConfirm(false)
      setSidebarOpen(false)
      navigate('/')
    }
  }

  return (
    <div className="admin-layout" style={{ display: 'grid', gridTemplateColumns: '238px 1fr', minHeight: '100vh' }}>
      {/* Desktop sidebar */}
      <aside className="hide-mobile" style={{
        background: 'var(--accent)', borderRight: '1px solid var(--line)',
        padding: '24px 18px', display: 'flex', flexDirection: 'column',
      }}>
        <SidebarContent onLogout={() => setShowConfirm(true)} user={user} />
      </aside>

      {/* Mobile sidebar overlay */}
      <div
        className={`admin-sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <aside className={`admin-sidebar ${sidebarOpen ? 'open' : ''}`} style={{
        background: 'var(--accent)', borderRight: '1px solid var(--line)',
        padding: '24px 18px', flexDirection: 'column',
      }}>
        <SidebarContent onLogout={() => setShowConfirm(true)} user={user} />
      </aside>

      <button
        className="admin-mobile-toggle"
        onClick={() => setSidebarOpen(true)}
        aria-label="Abrir menú"
        style={{
          display: 'none',
          position: 'fixed', top: 16, left: 16, zIndex: 20,
          width: 40, height: 40, borderRadius: '50%',
          background: 'var(--accent)', border: '1px solid var(--line)',
          color: '#fff', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', boxShadow: '0 4px 12px rgba(0,0,0,.15)',
        }}
      >
        <Menu size={20} />
      </button>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <main style={{ padding: '28px 34px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </main>
      </div>

      {showConfirm && (
        <ConfirmModal
          onConfirm={handleLogout}
          onCancel={() => setShowConfirm(false)}
          mensaje="Vas a salir del panel de administración. ¿Seguro?"
        />
      )}

      <style>{`
        @media (max-width: 860px) {
          .admin-mobile-toggle { display: flex !important; }
        }
      `}</style>
    </div >
  )
}
