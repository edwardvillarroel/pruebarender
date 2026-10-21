"""Modelos ORM de infraestructura.

Este `__init__` importa TODOS los modelos a proposito. Entre ellos se referencian
por nombre de clase (`db.relationship("PedidoModel")`), no por import directo,
as que SQLAlchemy los resuelve en el momento de configurar los mappers: hace
falta que todos esten registrados en el registry, no solo los que se importaron
por el camino.

Sin este archivo, importar un modelo suelto (por ejemplo
`app.infrastructure.database.models.producto_model`) dejaba el registry a medias
y el `relationship` de otro modelo no encontraba su contraparte: el fallo
aparecia al instanciar cualquier modelo, lejos de la causa.
"""

from app.infrastructure.database.models.carrito_model import CarritoItemModel, CarritoModel
from app.infrastructure.database.models.categoria_model import CategoriaModel
from app.infrastructure.database.models.detalle_pedido_model import DetallePedidoModel
from app.infrastructure.database.models.log_auditoria_model import LogAuditoriaModel
from app.infrastructure.database.models.notificacion_model import NotificacionModel
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.database.models.resena_model import ResenaModel
from app.infrastructure.database.models.solicitud_diseno_model import SolicitudDisenoModel
from app.infrastructure.database.models.usuario_model import UsuarioModel
from app.infrastructure.database.models.venta_local_model import (
    SesionVentaModel,
    VentaLocalItemModel,
    VentaLocalModel,
)

__all__ = [
    "CarritoItemModel",
    "CarritoModel",
    "CategoriaModel",
    "DetallePedidoModel",
    "LogAuditoriaModel",
    "NotificacionModel",
    "PagoModel",
    "PedidoModel",
    "ProductoColorModel",
    "ProductoModel",
    "ResenaModel",
    "SesionVentaModel",
    "SolicitudDisenoModel",
    "UsuarioModel",
    "VentaLocalItemModel",
    "VentaLocalModel",
]
