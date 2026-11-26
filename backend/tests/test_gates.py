import importlib.util
import os
import re

_spec = importlib.util.spec_from_file_location(
    "gates", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "gates.py"))
gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gates)
_SECRET = re.compile("|".join(gates.SECRET_PATTERNS))


def test_secret_scan_catches_key_shapes():
    # Built at runtime so this file never contains a key-shaped literal itself.
    samples = ["AIza" + "x" * 35, "token = AQ." + "Ab8R" * 10, "sk-" + "a1" * 12,
               "-----BEGIN RSA " + "PRIVATE KEY-----"]
    assert all(_SECRET.search(s) for s in samples)


def test_secret_scan_ignores_ordinary_text():
    assert not _SECRET.search('GEMINI_API_KEY = "<your key>"  # set it in your shell')
    assert not _SECRET.search("FR-LOAN-001 AQ. short")
