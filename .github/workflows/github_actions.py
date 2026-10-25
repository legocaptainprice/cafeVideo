import sys
from pathlib import Path
from sqlalchemy import create_engine, text
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DB_PATH = Path(__file__).resolve().parents[1] / "cafeDatabase.db"
DB_engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")

from main import cafe

def connect_to_database():
    return DB_engine.connect()


def test_github_actions():
    # This test only tests routes accessed by anonymous and logged in users
    # This does not test authentication, uploads, etc

    username = "github_actions_test"
    password = "testpassword"


    with cafe.test_client() as client:
        response = client.post("/registerAccount", data={"username": username, "password": password})
        print(f"Registration: HTTP {response.status_code}")

        response = client.post("/loginAuth", data={"username": username, "password": password})
        with client.session_transaction() as session:
            print(f"Session: {dict(session)}")

        # We insert a dummy video to test the watch page

        conn = connect_to_database()

        datetimeOfPublishedVideo = int(time.time())

        conn.execute(text("""INSERT INTO videos (userID, videoTitle, videoDescription, videoTags, videoFile, 
                                    videoThumbnail, datetime) VALUES (:userID, :videoTitle, :videoDescription, :videoTags, 
                                    :videoFile, :videoThumbnail, :datetime)"""),
                        {"userID": 1, "videoTitle": "dummy_video", "videoDescription": "dummy_video_description", "videoTags":
                            "dummy_video_tag", "videoFile": "dummy_video.mp4", "videoThumbnail": "dummy_thumbnail.png",
                        "datetime": datetimeOfPublishedVideo})
        conn.commit()
        conn.close()

        # We test all the routes

        pages = [
            "/",
            "/explore",
            "/subscriptions",
            "/history/videos",
            "/likes/videos",
            "/saves",
            "/corners",
            "/upload",
            "/notifications/all",
            "/help/license",
            "/help/notice",
            "/help/guidelines",
            "/about",
            "/results?search_query=test",
            "/channel?id=1",
            "/watch?v=1"
        ]
        for page in pages:
            response = client.get(page)
            print(f"{page} -> HTTP {response.status_code}")