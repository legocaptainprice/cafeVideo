import os
import shutil
import sys
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("SECRET_CAFE_KEY", "test-only-secret-key")

import main
import sql_commands


@pytest.fixture
def application(tmp_path, monkeypatch):
    test_database_url = os.environ.get("CAFE_TEST_DATABASE_URL")
    if test_database_url:
        engine = create_engine(test_database_url)
        if engine.dialect.name not in {"mysql", "postgresql"}:
            raise ValueError(f"Unsupported integration-test database: {engine.dialect.name}")
        schema_path = PROJECT_ROOT / "sql" / (
            "mysql.sql" if engine.dialect.name == "mysql" else "postgresql.sql"
        )
        with engine.begin() as connection:
            for statement in schema_path.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement).close()
    else:
        database_path = tmp_path / "cafeDatabase.db"
        shutil.copy2(PROJECT_ROOT / "cafeDatabase.db", database_path)
        engine = create_engine(f"sqlite:///{database_path}")
    monkeypatch.setattr(sql_commands, "DB_engine", engine)
    monkeypatch.setattr(sql_commands, "_corner_schema_engine", None)
    monkeypatch.setitem(main.cafe.config, "TESTING", True)
    monkeypatch.setitem(main.cafe.config, "PROPAGATE_EXCEPTIONS", True)
    main.cafe.config["UPLOAD_FOLDER"] = str(PROJECT_ROOT / "static" / "videos")
    main.cafe.config["UPLOAD_THUMBNAILS_FOLDER"] = str(PROJECT_ROOT / "static" / "thumbnails")
    main.cafe.config["UPLOAD_PROFILE_PICTURE_FOLDER"] = str(tmp_path / "profile-pictures")
    main.cafe.config["UPLOAD_PROFILE_BANNER_FOLDER"] = str(tmp_path / "profile-banners")
    Path(main.cafe.config["UPLOAD_PROFILE_PICTURE_FOLDER"]).mkdir()
    Path(main.cafe.config["UPLOAD_PROFILE_BANNER_FOLDER"]).mkdir()
    yield engine
    engine.dispose()
    monkeypatch.setattr(sql_commands, "_corner_schema_engine", None)


def register_and_login(client, username):
    password = "test-password-123"
    response = client.post(
        "/registerAccount",
        data={"username": username, "password": password},
    )
    assert response.status_code == 302
    client.get("/logout")
    response = client.post(
        "/loginAuth",
        data={"username": username, "password": password},
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["username"] == username
        assert "userID" in session
        user_id = session["userID"]
    return user_id, password


def scalar(engine, query, parameters=None):
    with engine.connect() as connection:
        return connection.execute(text(query), parameters or {}).scalar()


def test_database_mapping_keys_are_case_stable():
    row = main.sql_commands._canonicalize_mapping({
        "cornerid": 7,
        "creatorusername": "creator",
        "membercount": 2,
        "userid": 9,
    })
    assert row == {
        "cornerID": 7,
        "creatorUsername": "creator",
        "memberCount": 2,
        "userID": 9,
    }


def test_manifest_versions_preserve_build_numbers_across_channels():
    assert main.manifest.full_version(115, "alpha") == "1.0.0.build115.alpha"
    assert main.manifest.full_version(116, "beta") == "1.0.0.build116.beta"
    assert main.manifest.full_version(117, "rc") == "1.0.0.build117.rc"
    assert main.manifest.full_version(118, "release") == "1.0.0.build118.release"
    assert main.manifest.display_version(117, "rc") == "1.0.0.build117.rc"
    assert main.manifest.release_tag(118, "release") == "v1.0.0.build118.release"
    with pytest.raises(ValueError, match="Unsupported release channel"):
        main.manifest.full_version(104, "preview")


def test_routes_and_end_to_end_user_flows(application, tmp_path):
    engine = application
    token = uuid.uuid4().hex[:10]
    creator_name = f"creator_{token}"
    member_name = f"member_{token}"
    declining_name = f"decliner_{token}"
    video_name = f"test_video_{token}.mp4"
    fallback_video_name = f"fallback_video_{token}.mp4"
    thumbnail_name = f"test_thumbnail_{token}.png"
    uploaded_files = [
        PROJECT_ROOT / "static" / "videos" / video_name,
        PROJECT_ROOT / "static" / "videos" / fallback_video_name,
        PROJECT_ROOT / "static" / "thumbnails" / thumbnail_name,
    ]

    anonymous = main.cafe.test_client()
    creator = main.cafe.test_client()
    member = main.cafe.test_client()
    decliner = main.cafe.test_client()

    try:
        creator_id, _ = register_and_login(creator, creator_name)
        member_id, _ = register_and_login(member, member_name)
        decliner_id, _ = register_and_login(decliner, declining_name)
        assert sql_commands.validate_userID(creator_id) is not None
        assert sql_commands.validate_userID(creator_id + 100000) is None

        with engine.begin() as connection:
            admin_role_id = connection.execute(
                text("SELECT roleID FROM roles WHERE roleName = 'Admin'")
            ).scalar_one()
            connection.execute(
                text("INSERT INTO user_roles (userID, roleID) VALUES (:userID, :roleID)"),
                {"userID": creator_id, "roleID": admin_role_id},
            )

        # Upload a small test file through the same multipart route used by the UI.
        response = creator.post(
            "/uploadVideo",
            data={
                "title": f"Test video {token}",
                "description": "Uploaded by the integration test",
                "videoTags": "test,ci",
                "video": (BytesIO(b"test video bytes"), video_name),
                "thumbnail": (BytesIO(b"test thumbnail bytes"), thumbnail_name),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302
        video_id = scalar(
            engine,
            "SELECT videoID FROM videos WHERE videoFile = :videoFile",
            {"videoFile": video_name},
        )
        assert video_id is not None

        response = creator.post(
            "/uploadVideo",
            data={
                "title": f"Fallback video {token}",
                "description": "Uses the default thumbnail",
                "videoTags": "",
                "video": (BytesIO(b"fallback test video"), fallback_video_name),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302
        assert scalar(
            engine,
            "SELECT videoThumbnail FROM videos WHERE videoFile = :videoFile",
            {"videoFile": fallback_video_name},
        ) == "videotemplate.png"
        assert creator.post(
            "/uploadVideo",
            data={
                "title": "Invalid extension",
                "description": "Must not upload",
                "videoTags": "",
                "video": (BytesIO(b"invalid file"), f"invalid_{token}.txt"),
            },
            content_type="multipart/form-data",
        ).status_code == 400

        response = creator.get("/watch", query_string={"v": video_id})
        assert response.status_code == 200
        assert b"Test video" in response.data
        assert creator.get("/watch", query_string={"v": video_id + 100000}).status_code == 404

        with creator.session_transaction() as session:
            session["replyToCommentID"] = None
        assert creator.post(
            "/postComment",
            data={"postComment": "Creator test comment"},
        ).status_code == 302
        comment_id = scalar(
            engine,
            "SELECT commentID FROM comments WHERE videoID = :videoID AND userID = :userID",
            {"videoID": video_id, "userID": creator_id},
        )
        assert comment_id is not None
        with creator.session_transaction() as session:
            session["replyToCommentID"] = comment_id
        assert creator.post(
            "/postReply",
            data={"postReply": "Creator test reply"},
        ).status_code == 302
        reply_id = scalar(
            engine,
            "SELECT replyID FROM replies WHERE commentID = :commentID",
            {"commentID": comment_id},
        )
        assert reply_id is not None

        # Exercise subscriptions, likes, comments, replies, playlists, and saves.
        referrer = {"HTTP_REFERER": f"/watch?v={video_id}"}
        assert member.post(
            "/subscribeUser",
            query_string={"creatorID": creator_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert member.post(
            "/likeVideo",
            query_string={"videoID": video_id, "creatorID": creator_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert member.post(
            "/likeComment",
            query_string={"commentID": comment_id, "commenterID": creator_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert member.post(
            "/likeReply",
            query_string={"replyID": reply_id, "replierID": creator_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert scalar(engine, "SELECT COUNT(*) FROM subscriptions") == 1
        assert scalar(engine, "SELECT COUNT(*) FROM likedVideos") == 1
        assert scalar(engine, "SELECT COUNT(*) FROM likedComments") == 1
        assert scalar(engine, "SELECT COUNT(*) FROM likedReplies") == 1
        assert creator.post(
            "/searchRequest",
            data={"search": f"Test video {token}"},
        ).status_code == 302

        assert creator.post(
            "/playlists/create",
            data={
                "name": f"Test playlist {token}",
                "description": "Created by integration test",
                "visibility": "Public",
            },
            environ_overrides=referrer,
        ).status_code == 302
        playlist_id = scalar(
            engine,
            "SELECT playlistID FROM playlists WHERE userID = :userID AND playlistType = 'Regular'",
            {"userID": creator_id},
        )
        assert playlist_id is not None
        assert creator.post(
            f"/playlist/{playlist_id}/add",
            query_string={"v": video_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert creator.post(
            "/saves/add",
            query_string={"v": video_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT COUNT(*) FROM playlist_contents WHERE playlistID = :playlistID",
            {"playlistID": playlist_id},
        ) == 1

        # Exercise profile picture, banner, biography, and theme updates.
        response = creator.post(
            "/confirmProfileEdit",
            data={
                "bio": "Integration test profile",
                "profileTheme": "5",
                "profilePicture": (BytesIO(b"profile image"), f"profile_{token}.png"),
                "profileBanner": (BytesIO(b"profile banner"), f"banner_{token}.png"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302
        assert scalar(
            engine,
            "SELECT profileBio FROM profiles WHERE userID = :userID",
            {"userID": creator_id},
        ) == "Integration test profile"
        assert scalar(
            engine,
            "SELECT profilePicture FROM profiles WHERE userID = :userID",
            {"userID": creator_id},
        ) == f"profile_{token}.png"
        assert scalar(
            engine,
            "SELECT profileBanner FROM profiles WHERE userID = :userID",
            {"userID": creator_id},
        ) == f"banner_{token}.png"

        updated_creator_name = f"updated_creator_{token}"
        creator_channel_url = f"channel-{token}"
        assert creator.post(
            "/confirmAccountEdit",
            data={"usernameEdit": updated_creator_name, "channelURL": creator_channel_url},
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT username FROM accounts WHERE userID = :userID",
            {"userID": creator_id},
        ) == updated_creator_name
        assert creator.get(f"/{creator_channel_url}").status_code == 200
        assert creator.get("/account/settings").status_code == 200
        assert creator.get("/account/profile/edit").status_code == 200

        # Exercise Corner creation, custom and ID routes, invitations, acceptance, and decline.
        creator.get("/corner/create")
        with creator.session_transaction() as session:
            creator_csrf = session["corner_csrf_token"]
        response = creator.post(
            "/corner/create",
            data={
                "csrf_token": creator_csrf,
                "cornerName": f"Test Corner {token}",
                "cornerDescription": "Corner created by integration test",
                "cornerURLEnabled": "on",
                "cornerURL": f"test-corner-{token}",
            },
        )
        assert response.status_code == 302
        corner_id = scalar(
            engine,
            "SELECT cornerID FROM cafeCorners WHERE cornerURL = :cornerURL",
            {"cornerURL": f"test-corner-{token}"},
        )
        assert corner_id is not None
        assert creator.get(f"/corner/test-corner-{token}").status_code == 200
        assert creator.get("/corner/corner", query_string={"id": corner_id}).status_code == 302

        response = creator.post(
            f"/corner/{corner_id}/invite",
            data={"csrf_token": creator_csrf, "username": member_name},
        )
        assert response.status_code == 302
        assert scalar(
            engine,
            "SELECT COUNT(*) FROM notifications WHERE notificationItem = :item",
            {"item": f"corner-invite:{corner_id}"},
        ) == 1
        assert member.get("/notifications/all").status_code == 200
        with member.session_transaction() as session:
            member_csrf = session["corner_csrf_token"]
        assert member.post(
            "/corner/join",
            query_string={"cornerID": corner_id},
            data={"csrf_token": member_csrf},
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT COUNT(*) FROM cafeCornerMembers WHERE cornerID = :cornerID AND userID = :userID",
            {"cornerID": corner_id, "userID": member_id},
        ) == 1

        assert creator.post(
            f"/corner/{corner_id}/invite",
            data={"csrf_token": creator_csrf, "username": declining_name},
        ).status_code == 302
        assert decliner.get("/notifications/all").status_code == 200
        with decliner.session_transaction() as session:
            decliner_csrf = session["corner_csrf_token"]
        assert decliner.post(
            "/corner/decline",
            query_string={"cornerID": corner_id},
            data={"csrf_token": decliner_csrf},
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT invitationStatus FROM cornerInvitations WHERE invitedUserID = :userID",
            {"userID": decliner_id},
        ) == "declined"

        # Also cover a Corner that uses its numeric ID route.
        with creator.session_transaction() as session:
            creator_csrf = session["corner_csrf_token"]
        response = creator.post(
            "/corner/create",
            data={
                "csrf_token": creator_csrf,
                "cornerName": f"ID Corner {token}",
                "cornerDescription": "Corner with the numeric ID route",
            },
        )
        assert response.status_code == 302
        id_corner_id = scalar(
            engine,
            "SELECT cornerID FROM cafeCorners WHERE cornerName = :cornerName",
            {"cornerName": f"ID Corner {token}"},
        )
        assert id_corner_id is not None
        assert creator.get(
            "/corner/corner", query_string={"id": id_corner_id}
        ).status_code == 200

        # Exercise the admin-only listing and account suspension action.
        assert creator.get("/admin").status_code == 200
        with creator.session_transaction() as session:
            admin_csrf = session["admin_csrf_token"]
        assert creator.post(
            f"/admin/users/{decliner_id}/suspend",
            data={"csrf_token": admin_csrf},
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT accountStanding FROM accounts WHERE userID = :userID",
            {"userID": decliner_id},
        ) == "Suspended"
        assert member.get("/admin").status_code == 403
        assert anonymous.get("/admin").status_code == 403
        suspended_upload = decliner.post(
            "/uploadVideo",
            data={
                "title": "Suspended upload",
                "description": "Must be rejected",
                "videoTags": "",
                "video": (BytesIO(b"not authorized"), f"suspended_{token}.mp4"),
            },
            content_type="multipart/form-data",
        )
        assert suspended_upload.status_code == 403

        notification_id = scalar(
            engine,
            "SELECT notificationID FROM notifications WHERE notificationRecipientID = :userID "
            "ORDER BY notificationID DESC",
            {"userID": creator_id},
        )
        assert creator.post(
            "/notifications/actions/read",
            query_string={"id": notification_id},
            environ_overrides=referrer,
        ).status_code == 302
        assert scalar(
            engine,
            "SELECT notificationRead FROM notifications WHERE notificationID = :notificationID",
            {"notificationID": notification_id},
        ) == 1

        # Verify public and authenticated page routes in both session states.
        public_and_private_pages = [
            ("/", 302, 200),
            ("/login", 200, 302),
            ("/register", 200, 302),
            ("/loginAuth", 302, 302),
            ("/upload", 302, 200),
            (f"/watch?v={video_id}", 200, 200),
            (f"/results?search_query={token}", 200, 200),
            (f"/channel?id={creator_id}", 200, 200),
            (f"/{creator_channel_url}", 200, 200),
            ("/subscriptions", 302, 200),
            ("/explore", 200, 200),
            ("/likes/videos", 302, 200),
            ("/history/videos", 302, 200),
            ("/playlists/videos", 302, 200),
            (f"/playlist/{playlist_id}/videos", 200, 200),
            ("/saves", 302, 200),
            ("/about", 200, 200),
            ("/help/license", 200, 200),
            ("/help/notice", 200, 200),
            ("/help/guidelines", 200, 200),
            ("/corners", 302, 200),
            ("/corners/explore", 200, 200),
            ("/corner/create", 302, 200),
            (f"/corner/test-corner-{token}", 200, 200),
            (f"/corner/corner?id={id_corner_id}", 200, 200),
            ("/notifications/all", 200, 200),
            ("/test/template/run", 200, 200),
            (f"/api/videos/{video_id}", 200, 200),
            (f"/api/videos/{video_id}/stream", 200, 200),
        ]
        for path, anonymous_status, authenticated_status in public_and_private_pages:
            assert anonymous.get(path).status_code == anonymous_status, f"anonymous GET {path}"
            assert creator.get(path).status_code == authenticated_status, f"authenticated GET {path}"

        assert main.manifest.DISPLAY_VERSION.encode() in anonymous.get("/about").data

        expected_get_endpoints = {
            "aboutPage", "accountSubscriptions", "adminPage", "cornerCreate",
            "cornerProfileByID", "cornerProfileByURL", "cornersExplore", "cornersPage",
            "editUserProfile", "explorePage", "getAccountProfile", "getAccountSettings",
            "guidelines_page", "indexPage", "license_page", "likedVideosPage", "loginAuthAPI",
            "loginPage", "logout", "notice_page", "notificationsPage", "redirectPage",
            "registerPage", "retrieve_video_api", "retrieve_video_stream", "searchForVideo",
            "test_template", "upload", "userPlaylist", "viewPlaylist", "viewSaves",
            "watchHistory", "watchPage",
        }
        expected_post_endpoints = {
            "confirmAccountDetailsEdit", "cornerCreate", "cornerDeclineInvitation",
            "cornerInvite", "cornerJoin", "likeCommentFromCommenterID",
            "likeReplyFromReplierID", "likeVideoFromCreatorID", "loginAuthAPI",
            "notification_action_read", "playlistAdd", "playlistCreate", "registerAccountAPI",
            "saveProfileSettings", "saveVideo", "searchRequest", "sendComment", "sendReply",
            "subscribeToUser", "suspendAccount", "uploadVideo",
        }
        registered_get_endpoints = {
            rule.endpoint
            for rule in main.cafe.url_map.iter_rules()
            if "GET" in rule.methods and rule.endpoint != "static"
        }
        registered_post_endpoints = {
            rule.endpoint
            for rule in main.cafe.url_map.iter_rules()
            if "POST" in rule.methods and rule.endpoint != "static"
        }
        assert registered_get_endpoints == expected_get_endpoints
        assert registered_post_endpoints == expected_post_endpoints

        assert creator.get(f"/api/videos/{video_id}").json["Title"] == f"Test video {token}"
        assert anonymous.get(f"/api/videos/{video_id + 100000}").status_code == 404
        assert anonymous.post(
            "/loginAuth",
            data={"username": creator_name, "password": "incorrect-password"},
        ).status_code == 302

        # Unauthenticated writes must not create data or files.
        unauthenticated_upload = anonymous.post(
            "/uploadVideo",
            data={
                "title": "Unauthenticated upload",
                "description": "Must be rejected",
                "videoTags": "",
                "video": (BytesIO(b"not authorized"), f"anonymous_{token}.mp4"),
            },
            content_type="multipart/form-data",
        )
        assert unauthenticated_upload.status_code == 302
        assert not (PROJECT_ROOT / "static" / "videos" / f"anonymous_{token}.mp4").exists()
        assert creator.get("/logout").status_code == 302
        with creator.session_transaction() as session:
            assert "userID" not in session
    finally:
        for uploaded_file in uploaded_files:
            uploaded_file.unlink(missing_ok=True)
