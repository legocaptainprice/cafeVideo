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


def test_profile_page():
    username = "github_actions"
    password = "testpassword"
    channel_url = "github_actions"

    print("\n=== PROFILE PAGE TEST ===")

    with cafe.test_client() as client:
        # Log in first so the session is established.
        login_response = client.post(
            "/loginAuth",
            data={"username": username, "password": password},
            follow_redirects=False,
        )
        assert login_response.status_code == 302
        print("LOGIN: Successful")

        # Save the channel URL through the actual account-edit route.
        edit_response = client.post(
            "/confirmAccountEdit",
            data={
                "usernameEdit": username,
                "channelURL": channel_url,
            },
            follow_redirects=False,
        )
        print(f"ACCOUNT EDIT: HTTP {edit_response.status_code}")
        print(f"Redirect: {edit_response.location}")

        assert edit_response.status_code == 302

        # Visit the profile using the saved channel URL.
        profile_response = client.get(f"/{channel_url}")

        print(f"PROFILE URL: /{channel_url}")
        print(f"PROFILE HTTP status: {profile_response.status_code}")
        print(f"Response content type: {profile_response.content_type}")

        assert profile_response.status_code == 200
        print("PROFILE RESULT: Page loaded successfully.")

    
