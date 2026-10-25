import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import cafe


def test_account_registration():
    with cafe.test_client() as client:
        response = client.post(
            "/registerAccount",
            data={
                "username": "github_actions",
                "password": "testpassword"
            },
            follow_redirects=False
        )

        assert response.status_code == 302
