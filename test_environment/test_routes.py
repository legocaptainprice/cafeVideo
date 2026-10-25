import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DB_PATH = Path(__file__).resolve().parents[1] / "cafeDatabase.db"
DB_engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")

from main import cafe

def connect_to_database():
    return DB_engine.connect()


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

    with connect_to_database() as conn:
        result = conn.execute(
            text("SELECT * FROM accounts WHERE username = :username"),
            {"username": username},
        )
        account = result.fetchone()
        print(account)

    assert account is not None, (
        f"Registration failed: account '{username}' was not found "
        "in cafeDatabase.db"
    )

    
