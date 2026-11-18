

from __future__ import annotations

from uuid import UUID

from app.domain.entities.documento_tributario import DocumentoTributario
from app.domain.interfaces.repositories import DocumentoTributarioRepository


class ConsultarDocumentoTributario:
    def __init__(self, documentos: DocumentoTributarioRepository) -> None:
        self._documentos = documentos

    def por_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        return self._documentos.get_by_pedido(pedido_id)
