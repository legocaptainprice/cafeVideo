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
    username = "github_actions"
    
    with cafe.test_client() as client:
        response = client.post(
            "/registerAccount",
            data={
                "username": username,
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


def test_account_login():
    username = "github_actions"
    password = "testpassword"

    print("\n=== LOGIN TEST ===")

    with cafe.test_client() as client:
        print(f"Submitting login for: {username}")

        response = client.post(
            "/loginAuth",
            data={
                "username": username,
                "password": password,
            },
            follow_redirects=False,
        )

        print(f"Login HTTP status: {response.status_code}")
        print(f"Redirect location: {response.location}")

        assert response.status_code == 302
        assert response.location is not None

        with client.session_transaction() as session:
            print(f"Session contents: {dict(session)}")

            assert session.get("username") == username
            assert session.get("userID") is not None

    print("LOGIN RESULT: Authentication succeeded.")

    
