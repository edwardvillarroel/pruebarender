


from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from app.domain.entities.seguimiento_starken import (
    EventoSeguimiento,
    SeguimientoStarken,
)
from app.domain.interfaces.starken import StarkenSeguimientoCliente
from app.domain.time import utcnow

FASES = [
    ("INGRESADO", "Solicitud de despacho ingresada en Starken"),
    ("EN TRANSITO", "La orden de flete se encuentra en tránsito"),
    ("EN BODEGA SUCURSAL", "El paquete llegó a la bodega de la sucursal destino"),
    ("EN RUTA DE ENTREGA", "El repartidor lleva el paquete en ruta al domicilio"),
    ("ENTREGADO", "El paquete fue entregado al destinatario"),
]


class StarkenClienteSimulado(StarkenSeguimientoCliente):

    def __init__(self, config: dict) -> None:
        del config

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
