"""Consulta del documento electrónico de un pedido.

Sirve para mostrar el estado de la emisión (folio, token, error) y para
entregar el PDF del comprobante.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.entities.documento_tributario import DocumentoTributario
from app.domain.interfaces.repositories import DocumentoTributarioRepository


class ConsultarDocumentoTributario:
    def __init__(self, documentos: DocumentoTributarioRepository) -> None:
        self._documentos = documentos

    def por_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        """Documento del pedido, o `None` si todavía no se emitió nada."""
        return self._documentos.get_by_pedido(pedido_id)
