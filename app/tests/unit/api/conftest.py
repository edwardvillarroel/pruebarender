"""Fixtures de tests de la API (sin base de datos).

Los endpoints auditados (`@auditar`) persisten via `AUDITORIA_SERVICE`; en
los tests unitarios se mockea para no tocar la base. La frontera gateway ->
backend exige `X-Internal-Secret` cuando `INTERNAL_SECRET` esta configurado
(fail-closed, OWASP A01): en tests se fija un secreto compartido.
"""

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def _auditoria_service_mock(app):
    app.config["AUDITORIA_SERVICE"] = Mock()
    app.config["INTERNAL_SECRET"] = "secreto-interno-test"
    yield app
