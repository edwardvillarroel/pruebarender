import { Routes, Route } from 'react-router-dom'

import Navbar from './components/Navbar.jsx'
import TopBar from './components/TopBar.jsx'
import Footer from './components/Footer.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import ScrollToTop from './components/ScrollToTop.jsx'
import RutaCliente from './components/RutaCliente..jsx'
import RutaNoAdmin from './components/RutaNoAdmin.jsx'

import Home from './pages/Home.jsx'
import Categorias from './pages/Categorias.jsx'
import ProductoDetalle from './pages/ProductoDetalle.jsx'
import Carrito from './pages/Carrito.jsx'
import Checkout from './pages/Checkout.jsx'
import PagoRetorno from './pages/PagoRetorno.jsx'
import Cotizacion from './pages/Cotizacion.jsx'
import MisPedidos from './pages/MisPedidos.jsx'
import MisCotizaciones from './pages/MisCotizaciones.jsx'
import NotFound from './pages/NotFound.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

import AdminLayout from './pages/admin/AdminLayout.jsx'
import Dashboard from './pages/admin/Dashboard.jsx'
import Pedidos from './pages/admin/Pedidos.jsx'
import RegistrarVentaLocal from './pages/admin/RegistrarVentaLocal.jsx'
import Inventario from './pages/admin/Inventario.jsx'
import Cotizaciones from './pages/admin/Cotizaciones.jsx'
import ReportesVentas from './pages/admin/ReportesVentas.jsx'
import CuponesAdmin from './pages/admin/CuponesAdmin.jsx'
import WhatsAppFlotante from './components/whatsAppFlotante.jsx'
import AvisoMfaAdmin from './components/AvisoMfaAdmin.jsx'

function TiendaLayout({ children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
      <TopBar />
      <Navbar />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>
      <Footer />
      <WhatsAppFlotante />
    </div>
  )
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <AvisoMfaAdmin />
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<TiendaLayout><Home /></TiendaLayout>} />
          <Route path="/categorias" element={<TiendaLayout><Categorias /></TiendaLayout>} />
          <Route path="/producto/:id" element={<TiendaLayout><ProductoDetalle /></TiendaLayout>} />
          <Route path="/carrito" element={<TiendaLayout><RutaNoAdmin><Carrito /></RutaNoAdmin></TiendaLayout>} />
          <Route path="/checkout" element={<TiendaLayout><RutaNoAdmin><Checkout /></RutaNoAdmin></TiendaLayout>} />
          <Route path="/pago/retorno" element={<TiendaLayout><PagoRetorno /></TiendaLayout>} />
          <Route path="/cotizar" element={<TiendaLayout><RutaCliente><Cotizacion /></RutaCliente></TiendaLayout>} />
          <Route path="/mis-pedidos" element={<TiendaLayout><MisPedidos /></TiendaLayout>} />
          <Route path="/mis-cotizaciones" element={<TiendaLayout><MisCotizaciones /></TiendaLayout>} />

          <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="pedidos" element={<Pedidos />} />
            <Route path="venta" element={<RegistrarVentaLocal />} />
            <Route path="inventario" element={<Inventario />} />
            <Route path="cotizaciones" element={<Cotizaciones />} />
            <Route path="reportes" element={<ReportesVentas />} />
            <Route path="cupones" element={<CuponesAdmin />} />
          </Route>
          <Route path="*" element={<TiendaLayout><NotFound /></TiendaLayout>} />
        </Routes>
      </ErrorBoundary>
    </>
  )
}
