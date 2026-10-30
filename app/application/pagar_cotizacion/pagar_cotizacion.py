from uuid import uuid4
from app.domain.interfaces.pasarela_pago import SolicitudPago
from app.domain.entities.solicitud_diseno import EstadoSolicitud

class PagarCotizacion:
    def __init__(self, repo_cotizaciones, pasarela_pago):
        self.repo = repo_cotizaciones
        self.pasarela = pasarela_pago

    def ejecutar(self, usuario, cotizacion_id: str):
        cot = self.repo.obtener_por_id(cotizacion_id)
        if not cot:
            raise ValueError("Cotización no encontrada")
        if str(cot.usuario_id) != str(usuario.id):
            raise ValueError("No autorizado")
        if cot.estado != EstadoSolicitud.APROBADA:
            raise ValueError("La cotización debe estar aprobada")
        if not cot.precio or float(cot.precio) <= 0:
            raise ValueError("La cotización no tiene precio asignado")

        solicitud_pago = SolicitudPago(
            monto=int(float(cot.precio)), 
            email_cliente=usuario.email,
            nombre_cliente=usuario.nombre or cot.nombre,
            apellido_cliente=usuario.apellido or "",
            telefono_cliente=cot.telefono or "",
            descripcion=f"Cotizacion Apolo Vibes {cot.nombre} #{str(cot.id)[:8]}",
            referencia=f"COT-{str(cot.id)[:8]}-{uuid4().hex[:6].upper()}",
        )

        resultado = self.pasarela.crear_intento(solicitud_pago)
        return {"url": resultado.url, "token": resultado.token, "referencia": solicitud_pago.referencia}