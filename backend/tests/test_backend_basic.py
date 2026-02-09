"""
Test backend FastAPI: import base e setup minimo.

Test minimo per far sì che coverage raccolga dati sul package app.
Elimina il warning "No data was collected" quando si esegue make test-coverage
senza test che eseguono codice FastAPI.
"""
import pytest


def test_app_package_importable():
    """Import del package app per attivare la raccolta coverage su app/."""
    import app  # noqa: F401
    assert app is not None
