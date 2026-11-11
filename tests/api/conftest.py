from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcamento_pecas.api.app import criar_app


@pytest.fixture
def app(banco_teste: Path):
    return criar_app(banco_teste)


@pytest.fixture
def cliente(app):
    with TestClient(app) as cliente:
        yield cliente
