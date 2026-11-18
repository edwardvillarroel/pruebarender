

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def _auditoria_service_mock(app):
    app.config["AUDITORIA_SERVICE"] = Mock()
    app.config["INTERNAL_SECRET"] = "secreto-interno-test"
    yield app
