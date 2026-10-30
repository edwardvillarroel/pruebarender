from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.domain.entities.solicitud_diseno import SolicitudDiseno
from app.domain.entities.venta_local import VentaLocal
from app.domain.enums import EstadoPedido, EstadoSolicitudDiseno, MedioPago
from app.domain.interfaces.repositories import PedidoRepository, SolicitudDisenoRepository
from app.domain.interfaces.venta_local_repository import VentaLocalRepository
from app.domain.time import ZONA_CHILE, hoy_chile

# Estados de pedido que siguen activos (por entregar / en curso). Los terminales
# (`entregados`, `cancelados`) ya no representan una orden pendiente de atención.
_ESTADOS_PEDIDO_ACTIVOS = frozenset(
    {
        EstadoPedido.PENDIENTE,
        EstadoPedido.EN_PRODUCCION,
        EstadoPedido.ENVIADO,
    }
)


def _fecha_chile(instante: datetime | None) -> date | None:
    """Fecha local de Chile de un instante del dominio.

    Los timestamps se guardan en UTC (`utcnow`), asi que agrupar por dia/mes/semana
    exige convertirlos primero a `America/Santiago`: si no, una venta de las 21:00
    en Chile (00:00 UTC del dia siguiente) caeria en el dia/mes equivocado. Un
    valor naive se interpreta como UTC, que es como lo escriben las entidades.
    """
    if instante is None:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(ZONA_CHILE).date()


class GestionarReporte:
    """Reporte general de ventas y pedidos para el panel de administracion.

    Agrega las ventas de las sesiones locales cerradas y los pedidos pagados de
    la tienda web como ingresos, y ademas resume los pedidos (con su estado) y
    las cotizaciones pendientes, armando lo que consume el dashboard.

    Solo consulta (lectura): no modifica ninguna tabla.
    """

    def __init__(
        self,
        ventas: VentaLocalRepository,
        pedidos: PedidoRepository,
        solicitudes: SolicitudDisenoRepository,
    ) -> None:
        self._ventas = ventas
        self._pedidos = pedidos
        self._solicitudes = solicitudes

    def resumen(self) -> dict[str, Any]:
        ventas = self._ventas_totales()
        pedidos = self._pedidos.list_pagados()
        solicitudes = self._solicitudes.listar_todos()

        return {
            "ventas": self._resumen_ventas(ventas, pedidos),
            "pedidos": self._resumen_pedidos(pedidos),
            "cotizaciones": self._resumen_cotizaciones(solicitudes),
        }

    # ------------------------------------------------------------------ ventas

    def _ventas_totales(self) -> list[VentaLocal]:
        """Todas las ventas registradas en sesiones locales cerradas."""
        ventas: list[VentaLocal] = []
        for sesion in self._ventas.listar_reportes():
            ventas.extend(self._ventas.obtener_ventas_de_sesion(sesion.id))
        return ventas

    def _ingresos(
        self, ventas: list[VentaLocal], pedidos: list[Any]
    ) -> list[dict[str, Any]]:
        """Ingresos unificados: ventas del local + pedidos de la tienda web pagados.

        Son dos fuentes distintas (una venta local no genera un pedido), asi que
        sumarlas no duplica montos. Cada ingreso queda con su fecha LOCAL de Chile
        y su medio de pago para poder agrupar por dia, mes o semana.
        """
        ingresos: list[dict[str, Any]] = []

        for venta in ventas:
            fecha = _fecha_chile(venta.creado_en)
            if fecha is None:
                continue
            ingresos.append(
                {
                    "fecha": fecha,
                    "total": float(venta.total or 0),
                    "medio_pago": venta.medio_pago or MedioPago.EFECTIVO.value,
                }
            )

        for pedido in pedidos:
            estado = str(getattr(pedido.estado, "value", pedido.estado))
            # Un pedido cancelado no es ingreso aunque conserve un pago historico.
            if estado == EstadoPedido.CANCELADO.value:
                continue
            fecha = _fecha_chile(pedido.creado_en)
            if fecha is None:
                continue
            ingresos.append(
                {
                    "fecha": fecha,
                    "total": float(pedido.total or 0),
                    # Las compras de la tienda web se pagan por la pasarela TUU.
                    "medio_pago": MedioPago.TUU.value,
                }
            )

        return ingresos

    def _resumen_ventas(
        self, ventas: list[VentaLocal], pedidos: list[Any] | None = None
    ) -> dict[str, Any]:
        hoy = hoy_chile()
        primer_del_mes = hoy.replace(day=1)
        ultimo_del_mes = (primer_del_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        ingresos = self._ingresos(ventas, pedidos or [])

        def en_rango(desde: date, hasta: date) -> list[dict[str, Any]]:
            return [i for i in ingresos if desde <= i["fecha"] <= hasta]

        def totales_de(filtrados: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "total": float(sum(i["total"] for i in filtrados)),
                "n_ventas": len(filtrados),
            }

        por_medio_pago: dict[str, dict[str, Any]] = {}
        for ingreso in ingresos:
            medio = ingreso["medio_pago"]
            bucket = por_medio_pago.setdefault(
                medio, {"medio_pago": medio, "total": 0.0, "n_ventas": 0}
            )
            bucket["total"] = float(bucket["total"]) + ingreso["total"]
            bucket["n_ventas"] += 1

        return {
            "total": totales_de(ingresos),
            "hoy": totales_de(en_rango(hoy, hoy)),
            "mes": totales_de(en_rango(primer_del_mes, ultimo_del_mes)),
            "por_medio_pago": [por_medio_pago[medio] for medio in sorted(por_medio_pago)],
            "semanas": self._semanas(ingresos, hoy=hoy),
        }

    def _semanas(
        self,
        ingresos: list[dict[str, Any]],
        hoy: date | None = None,
        cantidad: int = 5,
    ) -> list[dict[str, Any]]:
        """Totales por semana (lunes a domingo) de las ultimas `cantidad` semanas.

        `desde` es la fecha ISO del lunes de cada tramo: el frontend la usa como
        etiqueta del eje X (formato DD/MM). Las fechas ya vienen en hora de Chile.
        """
        hoy = hoy or hoy_chile()
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        semanas: list[dict[str, Any]] = []
        for i in range(cantidad - 1, -1, -1):
            inicio = lunes_actual - timedelta(weeks=i)
            fin = inicio + timedelta(days=7)
            total = float(
                sum(ingreso["total"] for ingreso in ingresos if inicio <= ingreso["fecha"] < fin)
            )
            semanas.append(
                {
                    "semana": inicio.isocalendar()[1],
                    "desde": inicio.isoformat(),
                    "hasta": (fin - timedelta(days=1)).isoformat(),
                    "total": total,
                }
            )
        return semanas

    # ------------------------------------------------------------------- pedidos

    def _resumen_pedidos(self, pedidos: list[Any]) -> dict[str, Any]:
        por_estado: dict[str, int] = {}
        for pedido in pedidos:
            clave = (
                pedido.estado.value if hasattr(pedido.estado, "value") else str(pedido.estado)
            )
            por_estado[clave] = por_estado.get(clave, 0) + 1

        pendientes = [p for p in pedidos if p.estado in _ESTADOS_PEDIDO_ACTIVOS]

        return {
            "recientes": [self._a_publico_pedido(p) for p in pedidos[:5]],
            "pendientes": [self._a_publico_pedido(p) for p in pendientes],
            "por_estado": [
                {"estado": estado, "total": total}
                for estado, total in sorted(por_estado.items())
            ],
        }

    def _a_publico_pedido(self, pedido: Any) -> dict[str, Any]:
        cliente = self._cliente(pedido)
        nombre = " ".join(
            parte
            for parte in (cliente.get("nombre"), cliente.get("apellido"))
            if parte
        ).strip()
        return {
            "id": str(pedido.id),
            "estado": (
                pedido.estado.value if hasattr(pedido.estado, "value") else str(pedido.estado)
            ),
            "total": float(pedido.total or 0),
            "fecha": pedido.creado_en.isoformat() if pedido.creado_en else None,
            "cliente": nombre,
            "entrega": pedido.entrega,
        }

    @staticmethod
    def _cliente(pedido: Any) -> dict[str, Any]:
        if not pedido.direccion_envio:
            return {}
        try:
            datos = json.loads(pedido.direccion_envio)
        except (TypeError, ValueError):
            return {}
        return datos if isinstance(datos, dict) else {}

    # -------------------------------------------------------------- cotizaciones

    def _resumen_cotizaciones(
        self, solicitudes: list[SolicitudDiseno]
    ) -> dict[str, Any]:
        sin_revisar = [
            self._a_publico_solicitud(s)
            for s in solicitudes
            if s.estado == EstadoSolicitudDiseno.PENDIENTE
        ]
        return {"sin_revisar": sin_revisar, "total": len(sin_revisar)}

    def _a_publico_solicitud(self, solicitud: SolicitudDiseno) -> dict[str, Any]:
        return {
            "id": str(solicitud.id),
            "nombre": solicitud.nombre,
            "email": solicitud.email,
            "estado": (
                solicitud.estado.value
                if hasattr(solicitud.estado, "value")
                else str(solicitud.estado)
            ),
            "creado_en": solicitud.creado_en.isoformat() if solicitud.creado_en else None,
            "precio": float(solicitud.precio) if solicitud.precio is not None else None,
        }

