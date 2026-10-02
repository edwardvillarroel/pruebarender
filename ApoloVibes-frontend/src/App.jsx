import { Routes, Route } from 'react-router-dom'

import Navbar from './components/Navbar.jsx'
import TopBar from './components/TopBar.jsx'
import Footer from './components/Footer.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import ScrollToTop from './components/ScrollToTop.jsx'

import Home from './pages/Home.jsx'
import Categorias from './pages/Categorias.jsx'
import ProductoDetalle from './pages/ProductoDetalle.jsx'
import Carrito from './pages/Carrito.jsx'
import Checkout from './pages/Checkout.jsx'
import PagoRetorno from './pages/PagoRetorno.jsx'
import CompraExitosa from './pages/CompraExitosa.jsx'
import Cotizacion from './pages/Cotizacion.jsx'
import MisPedidos from './pages/MisPedidos.jsx'
import NotFound from './pages/NotFound.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

import AdminLayout from './pages/admin/AdminLayout.jsx'
import Dashboard from './pages/admin/Dashboard.jsx'
import Pedidos from './pages/admin/Pedidos.jsx'
import RegistrarVentaLocal from './pages/admin/RegistrarVentaLocal.jsx'
import Inventario from './pages/admin/Inventario.jsx'
import Cotizaciones from './pages/admin/Cotizaciones.jsx'
import ReportesVentas from './pages/admin/ReportesVentas.jsx'

function TiendaLayout({ children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
      <TopBar />
      <Navbar />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<TiendaLayout><Home /></TiendaLayout>} />
          <Route path="/categorias" element={<TiendaLayout><Categorias /></TiendaLayout>} />
          <Route path="/producto/:id" element={<TiendaLayout><ProductoDetalle /></TiendaLayout>} />
          <Route path="/carrito" element={<TiendaLayout><Carrito /></TiendaLayout>} />
          <Route path="/checkout" element={<TiendaLayout><Checkout /></TiendaLayout>} />
          <Route path="/pago/retorno" element={<TiendaLayout><PagoRetorno /></TiendaLayout>} />
          <Route path="/compra-exitosa" element={<TiendaLayout><CompraExitosa /></TiendaLayout>} />
          <Route path="/cotizar" element={<TiendaLayout><Cotizacion /></TiendaLayout>} />
          <Route path="/mis-pedidos" element={<TiendaLayout><MisPedidos /></TiendaLayout>} />

          <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="pedidos" element={<Pedidos />} />
            <Route path="venta" element={<RegistrarVentaLocal />} />
            <Route path="inventario" element={<Inventario />} />
            <Route path="cotizaciones" element={<Cotizaciones />} />
            <Route path="reportes" element={<ReportesVentas />} />
          </Route>

          {/* Catch-all: debe quedar SIEMPRE al final de <Routes>. Una ruta "*"
              antes de las demás las desactivaría. Envuelve con TiendaLayout porque
              NotFound es layout-free (no monta TopBar/Navbar/Footer por su cuenta). */}
          <Route path="*" element={<TiendaLayout><NotFound /></TiendaLayout>} />
        </Routes>
      </ErrorBoundary>
    </>
  )
}
