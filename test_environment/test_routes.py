import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import cafe


def test_homepage_responds():
    with cafe.test_client() as client:
        response = client.get("/")
        assert response.status_code < 500
