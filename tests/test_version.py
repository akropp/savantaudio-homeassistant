"""Basic test to ensure pytest can discover and run tests."""
import pytest

from custom_components.savantaudio.const import DOMAIN, VERSION


def test_domain_constant():
    """Test domain constant."""
    assert DOMAIN == "savantaudio"


def test_version():
    """Test version is defined correctly."""
    assert VERSION == "1.0.3"
