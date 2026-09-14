

export default function RegistrarVentaLocal() {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, marginBottom: 24, color: 'var(--surface-2)' }}>Venta Local</h1>
            <button className="btn btn-primary">+  Nueva Venta</button>
        </div>
    )
}
