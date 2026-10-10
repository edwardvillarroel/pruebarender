"""Cliente de seguimiento Starken en MODO SIMULACIÓN (desarrollo).

Implementa la misma interfaz de dominio `StarkenSeguimientoCliente` que el
cliente real, pero sin hacer llamadas HTTP. Se inyecta vía DI cuando
`STARKEN_MODO_SIMULACION` está activo en la configuración; así el flujo de
pedidos, las rutas y el frontend se ejercitan con datos plausibles sin
necesitar la API key de la PYME.

Los estados son DETERMINISTAS por código: el mismo código siempre entrega el
mismo estado (hash), de modo que refrescar no "salta" de estado y cada pedido
muestra un hit o una fase distinta en el panel admin.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from app.domain.entities.seguimiento_starken import (
    EventoSeguimiento,
    SeguimientoStarken,
)
from app.domain.interfaces.starken import StarkenSeguimientoCliente
from app.domain.time import utcnow

# Fases del proceso de despacho en orden. El estado del pedido se elige según
# un hash del código para que distintos códigos muestren fases diferentes.
FASES = [
    ("INGRESADO", "Solicitud de despacho ingresada en Starken"),
    ("EN TRANSITO", "La orden de flete se encuentra en tránsito"),
    ("EN BODEGA SUCURSAL", "El paquete llegó a la bodega de la sucursal destino"),
    ("EN RUTA DE ENTREGA", "El repartidor lleva el paquete en ruta al domicilio"),
    ("ENTREGADO", "El paquete fue entregado al destinatario"),
]


class StarkenClienteSimulado(StarkenSeguimientoCliente):
    """Cliente de seguimiento que responde datos fabricados deterministas."""

    def __init__(self, config: dict) -> None:
        del config  # no usa credenciales; solo el flag lo selecciona

    def consultar(self, codigo: str) -> SeguimientoStarken:
        indice = int.from_bytes(
            hashlib.md5(codigo.encode("utf-8")).digest()[:2], "big"
        ) % len(FASES)
        estado, descripcion = FASES[indice]
        ahora = utcnow()

        eventos: list[EventoSeguimiento] = []
        for pos in range(0, indice + 1):
            estado_evento, texto = FASES[pos]
            eventos.append(
                EventoSeguimiento(
                    fecha=ahora - timedelta(days=indice - pos),
                    descripcion=texto,
                    sucursal="Bodega Central Santiago",
                    ciudad="Santiago",
                    estado=estado_evento,
                )
            )

        return SeguimientoStarken(
            codigo=codigo,
            estado=estado,
            descripcion=descripcion,
            historial=eventos,
            consultado_en=ahora,
        )
