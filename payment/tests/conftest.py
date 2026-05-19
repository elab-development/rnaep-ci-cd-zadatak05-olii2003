"""
Pytest konfiguracija i zajednički fixture-i za sve kategorije testova.
"""
import pytest
import os
from unittest.mock import MagicMock, patch


def pytest_configure(config):
    """Registrujemo custom markere."""
    config.addinivalue_line("markers", "unit: unit testovi - bez spoljnih zavisnosti")
    config.addinivalue_line("markers", "integration: integracioni testovi - zahtevaju Redis")
    config.addinivalue_line("markers", "functional: funkcionalni testovi - API nivo")


@pytest.fixture(autouse=True, scope="session")
def set_test_env():
    """Postavlja test env promenljive ako nisu već postavljene."""
    defaults = {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "",
    }
    for key, value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = value
    yield
