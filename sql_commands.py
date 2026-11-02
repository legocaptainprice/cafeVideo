import config

import random
import threading

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Text, bindparam, create_engine, text
from sqlalchemy.sql import quoted_name

from sqlalchemy.exc import IntegrityError

from collections import Counter

from datetime import datetime

import time

# Set the location for the database
DB_engine = create_engine(config.sqlalchemy_db_path)
_corner_schema_engine = None
_corner_schema_lock = threading.Lock()

corner_metadata = MetaData()
accounts_table = Table(
    quoted_name("accounts", quote=False), corner_metadata,
    Column(quoted_name("userID", quote=False), Integer, primary_key=True)
)
profile_color_sets_table = Table(
    quoted_name("profileColorSets", quote=False), corner_metadata,
    Column(quoted_name("profileSetID", quote=False), Integer, primary_key=True)
)
cafe_corners_table = Table(
    quoted_name("cafeCorners", quote=False), corner_metadata,
    Column(quoted_name("cornerID", quote=False), Integer, primary_key=True, autoincrement=True),
    Column(quoted_name("userID", quote=False), Integer,
           ForeignKey("accounts.userID", ondelete="CASCADE"), nullable=False),
    Column(quoted_name("cornerName", quote=False), Text),
    Column(quoted_name("cornerDescription", quote=False), Text),
    Column(quoted_name("cornerBanner", quote=False), Text),
    Column(quoted_name("cornerColorTheme", quote=False), Integer,
           ForeignKey("profileColorSets.profileSetID", ondelete="SET NULL")),
    Column(quoted_name("cornerURLEnabled", quote=False), Integer),
    Column(quoted_name("cornerURL", quote=False), Text),
    Column(quoted_name("creationDate", quote=False), Integer)
)
cafe_corner_members_table = Table(
    quoted_name("cafeCornerMembers", quote=False), corner_metadata,
    Column(quoted_name("cornerID", quote=False), Integer,
           ForeignKey("cafeCorners.cornerID", ondelete="CASCADE"), primary_key=True),
    Column(quoted_name("userID", quote=False), Integer,
           ForeignKey("accounts.userID", ondelete="CASCADE"), primary_key=True),
    Column("role", Text, nullable=False),
    Column(quoted_name("joinedDate", quote=False), Integer)
)
corner_invitations_table = Table(
    quoted_name("cornerInvitations", quote=False), corner_metadata,
    Column(quoted_name("invitationID", quote=False), Integer, primary_key=True, autoincrement=True),
    Column(quoted_name("cornerID", quote=False), Integer,
           ForeignKey("cafeCorners.cornerID", ondelete="CASCADE"), nullable=False),
    Column(quoted_name("inviterUserID", quote=False), Integer,
           ForeignKey("accounts.userID", ondelete="CASCADE"), nullable=False),
    Column(quoted_name("invitedUserID", quote=False), Integer,
           ForeignKey("accounts.userID", ondelete="CASCADE"), nullable=False),
    Column(quoted_name("invitationStatus", quote=False), Text, nullable=False, default="pending"),
    Column(quoted_name("createdAt", quote=False), Integer, nullable=False)
)


def connect_to_database():
    return DB_engine.connect()


_MAPPING_KEY_NAMES = {
    name.lower(): name
    for name in (
        "accountStanding", "channelURLEnabled", "channelURL", "cornerBanner",
        "cornerColorTheme", "cornerDescription", "cornerID", "cornerName",
        "cornerURL", "cornerURLEnabled", "creationDate", "creatorUsername",
        "displayName", "eventCSSDir", "eventHTMLDir", "eventID", "eventImagesDir",
        "eventJSDir", "eventName", "featureID", "invitationID", "inviterUsername",
        "joinedDate", "memberCount", "profileColorTheme", "profilePicture",
        "profilePictureBorderColor", "profileSetID", "role", "roleID",
        "roleName", "roleNames", "userID", "username",
    )
}


def _canonicalize_mapping(row):
    return {
        _MAPPING_KEY_NAMES.get(key.lower(), key): value
        for key, value in row.items()
    }


def _canonicalize_mappings(result):
    return [_canonicalize_mapping(row) for row in result.mappings()]


def _quote_identifier(identifier):
    return DB_engine.dialect.identifier_preparer.quote(identifier)


def fetch_latest_videos():
    """Fetch videos in the database in descending order"""
    conn = connect_to_database()

    # Fetch the latest videos for the new videos feed
    result = conn.execute(text("""
                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, 
                videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor, 
                profiles.channelURLEnabled, profiles.channelURL, accounts.accountStanding
                FROM videos
                JOIN accounts ON videos.userID = accounts.userID
                JOIN profiles ON profiles.userID = accounts.userID
                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                WHERE accountStanding != 'Suspended'
                ORDER BY videoID DESC  -- Shows newest first
            """))
    videos = result.fetchall()

    conn.close()

    return videos


def fetch_profile_info(variant, userID):
    """Fetch the profile of the user from the database"""
    conn = connect_to_database()

    if variant == "minimal":
        result = conn.execute(text("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                channelURL
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = :userID"""), {"userID": userID})
        profilePicture = result.fetchone()

        conn.close()

        return profilePicture
    if variant == "extended":
        result = conn.execute(text("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, profileBanner, 
                                channelURL, channelURLEnabled, profileBio, profileColorTheme
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = :userID"""), {"userID": userID})
        profilePicture = result.fetchone()

        conn.close()

        return profilePicture
    if variant == "profilePage":
        result = conn.execute(text("""
                                        SELECT * 
                                        FROM accounts 
                                        JOIN profiles ON accounts.userID = profiles.userID
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE accounts.userID = :userID
                                        """), {"userID": userID})
        profileDetails = result.fetchone()

        conn.close()

        return profileDetails
    if variant == "latestVideos":
        result = conn.execute(text("""
                                        SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime
                                        FROM videos
                                        JOIN accounts ON videos.userID = accounts.userID
                                        WHERE videos.userID = :userID
                                        ORDER BY videoID DESC  -- Shows newest first
                                    """), {"userID": userID})
        videos = result.fetchall()

        conn.close()

        return videos


def fetch_subscription_info(userID):
    """Fetches the user subscriptions from the database"""
    conn = connect_to_database()

    result = conn.execute(text("""
                            SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                            accounts.username, channelURLEnabled, channelURL, accounts.accountStanding
                            FROM profiles
                            JOIN accounts ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = :userID AND accountStanding != 'Suspended' """),
                          {"userID": userID})
    subscriptionsInfo = result.fetchall()

    conn.close()

    return subscriptionsInfo


def fetch_subscription_videos(variant, userID):
    """Fetches the user subscription videos from the database"""
    conn = connect_to_database()

    if variant == "latest":
        result = conn.execute(text("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                profileColorSets.profilePictureBorderColor, profiles.channelURLEnabled, profiles.channelURL
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                JOIN profiles ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = :userID AND accountStanding != 'Suspended'
                                ORDER BY videoID DESC  -- Shows newest first
                                LIMIT 12
                                """), {"userID": userID})
    if variant == "page":
        # Fetch the latest videos for the subscriptions feed
        result = conn.execute(text("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                            videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, accounts.accountStanding
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = :userID AND accountStanding != 'Suspended'
                            ORDER BY videoID DESC  -- Shows newest first
                        """), {"userID": userID})

    subscription_videos = result.fetchall()

    conn.close()

    return subscription_videos


def fetch_user_notifications(variant, userID):
    """Fetch user notifications from the database"""
    conn = connect_to_database()

    if variant == "minimal":
        result = conn.execute(text("""
                                SELECT notifications.*, profiles.profilePicture, profileColorSets.profilePictureBorderColor 
                                FROM notifications
                                JOIN profiles ON notifications.notificationSenderID = profiles.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE notificationRecipientID = :notificationRecipientID AND notificationRead != 1
                                ORDER BY notificationDateTime DESC
                                         """),
                              {"notificationRecipientID": userID})
        notifications = result.fetchall()

        result = conn.execute(text(
            """SELECT COUNT(*) FROM notifications 
               WHERE notificationRecipientID = :notificationRecipientID AND notificationRead != 1"""
        ), {"notificationRecipientID": userID})
        notificationsCount = result.fetchall()[0]

        conn.close()

        return notifications, notificationsCount[0]


def fetch_account_info(variant, userID):
    """Fetch the user account info from the database"""
    conn = connect_to_database()

    if variant == "feature_access":
        result = conn.execute(text("""
                                SELECT feature_access.featureID, feature_gating.featureName
                                FROM feature_access
                                JOIN feature_gating ON feature_access.featureID = feature_gating.featureID
                                JOIN accounts ON feature_access.userID = accounts.userID
                                WHERE accounts.userID = :userID  
                                """), {"userID": userID})
        featureAccess = result.fetchall()

        conn.close()

        return featureAccess


def fetch_user_playlist_info(variant, userID, videoID, playlistID):
    """Fetches the playlist info of a playlist made by the user"""
    conn = connect_to_database()

    if variant == "add":
        # Check if playlist exists and if it was made by the user
        result = conn.execute(text("SELECT * FROM playlists WHERE playlistID = :playlistID AND userID = :userID"),
                              {"playlistID": playlistID, "userID": userID})
        playlistExists = result.fetchone()

        if playlistExists:
            print(f"Playlist {playlistID} Found!")
            # Check if video is already in playlist
            result = conn.execute(
                text("SELECT * FROM playlist_contents WHERE playlistID = :playlistID AND videoID = :videoID"),
                {"playlistID": playlistID, "videoID": videoID})
            videoInPlaylist = result.fetchone()

            if videoInPlaylist:
                # If the video is already in the playlist then remove it from the playlist
                conn.execute(
                    text("DELETE FROM playlist_contents WHERE playlistID = :playlistID AND videoID = :videoID"),
                    {"playlistID": playlistID, "videoID": videoID})
                conn.commit()
                print("Video removed from playlist")
                conn.close()
            else:
                # If the video is not in the playlist then add it to the playlist
                conn.execute(text("INSERT INTO playlist_contents (playlistID, videoID) VALUES (:playlistID, :videoID)"),
                             {"playlistID": playlistID, "videoID": videoID})
                conn.commit()
                print("Video added to playlist")
                conn.close()

        else:
            print("Playlist Not Found!")


def add_to_user_saved_videos(userID, videoID):
    """Adds the video the user requested to save to the saved videos playlist"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM playlists WHERE userID = :userID and playlistType = :playlistType"),
                          {"userID": userID, "playlistType": "watch_queue"})
    userSavedVideos = result.fetchone()

    fetch_user_playlist_info("add", userID, videoID, userSavedVideos[0])


# This needs more explaining
def fetch_watch_page_details(variant, userID, videoID):
    """Fetches the necessary details from the database for the watch page for the selected video"""
    conn = connect_to_database()

    if variant == "saves":
        result = conn.execute(text("SELECT * FROM playlists WHERE userID = :userID and playlistType = :playlistType"),
                              {"userID": userID, "playlistType": "watch_queue"})
        userSavedVideos = result.fetchone()  # Retrieve the playlist where saved videos are stored

        result = conn.execute(
            text("SELECT * FROM playlist_contents WHERE playlistID = :playlistID AND videoID = :videoID"),
            {"playlistID": userSavedVideos[0], "videoID": videoID})
        isVideoSaved = result.fetchone()

        if isVideoSaved:
            return True
        else:
            return False


def fetch_user_watch_history(userID):
    """Fetches the user watch history from the database"""
    conn = connect_to_database()

    # Fetch the latest videos for the watch history section
    result = conn.execute(text("""
                        SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                        videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                        profileColorSets.profilePictureBorderColor, videos.videoTags, accounts.accountStanding
                        FROM videos
                        JOIN accounts ON videos.userID = accounts.userID
                        JOIN profiles ON profiles.userID = accounts.userID
                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                        JOIN watchHistory ON watchHistory.videoID = videos.videoID
                        WHERE watchHistory.userID = :userID AND accounts.accountStanding != 'Suspended'
                        ORDER BY watchHistory.historyDateTime DESC  -- Shows newest first
                        """), {"userID": userID})
    watchHistory = result.fetchall()

    conn.close()

    return watchHistory


def extract_tags_from_video(tags):
    tags = [tag.strip() for tag in tags.split(",")]

    return tags


def fetch_user_recommended_feed(userID):
    """Fetches the user recommended feed for the home page"""
    conn = connect_to_database()
    video_tags_list = []

    watchHistory = fetch_user_watch_history(userID)

    if watchHistory:
        for videoWatched in watchHistory:
            video_tags = videoWatched[8]

            video_tags_extracted = extract_tags_from_video(video_tags)

            try:
                for videoTag in video_tags_extracted:
                    video_tags_list.append(videoTag)
            except:
                pass

        rank_video_tags = Counter(video_tags_list)

        top_video_tags = [tag for tag, _ in rank_video_tags.most_common(10)]

        print(top_video_tags)
        if not top_video_tags:
            conn.close()
            return []

        tag_parameters = {}
        for i, tag in enumerate(top_video_tags):
            normalized_tag = tag.replace(" ", "").lower()
            tag_parameters.update({
                f"tag{i}_exact": normalized_tag,
                f"tag{i}_start": f"{normalized_tag},%",
                f"tag{i}_middle": f"%,{normalized_tag},%",
                f"tag{i}_end": f"%,{normalized_tag}",
            })

        result = conn.execute(text(f"""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, 
                            videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor, 
                            profiles.channelURLEnabled, profiles.channelURL, accounts.accountStanding
                            FROM videos 
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE ({" OR ".join([
                                f"(LOWER(REPLACE(videoTags, ' ', '')) = :tag{i}_exact "
                                f"OR LOWER(REPLACE(videoTags, ' ', '')) LIKE :tag{i}_start "
                                f"OR LOWER(REPLACE(videoTags, ' ', '')) LIKE :tag{i}_middle "
                                f"OR LOWER(REPLACE(videoTags, ' ', '')) LIKE :tag{i}_end)"
                                for i in range(len(top_video_tags))
                            ])}) AND accountStanding != 'Suspended'
                                    """), tag_parameters)
        recommended_videos = result.fetchall()
        conn.close()
    else:
        conn.close()
        recommended_videos = []

    return recommended_videos


def fetch_video_for_watch_page(videoID):
    """Fetches the queried video information from the database"""
    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                    FROM videos 
                                    JOIN profiles ON profiles.userID = videos.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE videoID = :videoID"""), {"videoID": videoID})
    video = result.fetchone()

    result = conn.execute(text("""
                    SELECT accountStanding
                    FROM videos
                    JOIN accounts ON accounts.userID = videos.userID
                    WHERE videoID = :videoID
                    """), {"videoID": videoID})
    accountStanding_row = result.fetchone()
    if not video or not accountStanding_row:
        conn.close()
        return None, None
    accountStanding_check = accountStanding_row[0]

    conn.close()

    return video, accountStanding_check


def fetch_comments_section(userID, videoID):
    """Fetches the comment section for the video"""
    conn = connect_to_database()

    result = conn.execute(text("""
                            SELECT comments.commentID, accounts.username, comments.comment, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, comments.userID,
                            (SELECT COUNT(*) FROM likedComments
                             WHERE likedComments.commentID = comments.commentID) AS likeCount,
                            (SELECT COUNT(*) FROM likedComments
                             WHERE likedComments.commentID = comments.commentID
                               AND likedComments.userID = :userID) AS isLikedByUser,
                            accounts.accountStanding
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE comments.videoID = :videoID AND accountStanding != 'Suspended'
                            ORDER BY comments.commentID DESC 
                            """), {"userID": userID, "videoID": videoID})
    comments = result.fetchall()

    return comments


def fetch_video_showcase_board():
    """Fetches the video showcase board for the login and register page"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT COUNT(*) FROM videos"))

    num_of_videos = result.fetchone()[0]

    if num_of_videos:
        video_showcase_1_randomizer = random.randint(1, num_of_videos)
        video_showcase_2_randomizer = random.randint(1, num_of_videos)
        video_showcase_3_randomizer = random.randint(1, num_of_videos)

        result = conn.execute(text("SELECT * FROM videos WHERE videoID = :videoID"),
                              {"videoID": video_showcase_1_randomizer})
        video_showcase_1 = result.fetchone()

        result = conn.execute(text("SELECT * FROM videos WHERE videoID = :videoID"),
                              {"videoID": video_showcase_2_randomizer})
        video_showcase_2 = result.fetchone()

        result = conn.execute(text("SELECT * FROM videos WHERE videoID = :videoID"),
                              {"videoID": video_showcase_3_randomizer})
        video_showcase_3 = result.fetchone()

        conn.close()

        return video_showcase_1, video_showcase_2, video_showcase_3

    print(f"Total videos: {num_of_videos}")


def fetch_search_results(searchType, searchQueryForDB, userID):
    """Fetches videos that match or are related to the search query from the user"""
    conn = connect_to_database()

    if searchType == "Regular":
        # Fetch the videos with the most views for the search results
        result = conn.execute(text("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                            videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, accounts.accountStanding
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE LOWER(videos.videoTitle) LIKE LOWER(:videoTitle) AND accountStanding != 'Suspended'
                            ORDER BY views DESC  -- Shows newest first
                        """), {"videoTitle": searchQueryForDB})
        resultsFromSearch = result.fetchall()
        conn.close()
        return resultsFromSearch
    if searchType == "Subscriptions":
        # Fetch the videos with the most views for the search results
        result = conn.execute(text("""
                                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                    profileColorSets.profilePictureBorderColor, accounts.accountStanding
                                    FROM videos
                                    JOIN accounts ON videos.userID = accounts.userID
                                    JOIN profiles ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE LOWER(videos.videoTitle) LIKE LOWER(:videoTitle) AND subscriptions.userID = :userID AND accountStanding != 'Suspended'
                                    ORDER BY views DESC  -- Shows newest first
                                """), {"videoTitle": searchQueryForDB, "userID": userID})
        resultsFromSearch = result.fetchall()
        conn.close()
        return resultsFromSearch


def fetch_account_standing(userID):
    """Fetches the account standing for a given userID"""
    with connect_to_database() as conn:
        result = conn.execute(
            text("SELECT accountStanding FROM accounts WHERE userID = :userID"),
            {"userID": userID}
        )
        row = result.first()
        return row[0] if row else None


def initialize_corner_schema():
    """Create the Corner tables when upgrading an existing database."""
    global _corner_schema_engine
    with _corner_schema_lock:
        if _corner_schema_engine is DB_engine:
            return
        if DB_engine.dialect.name in {"mysql", "postgresql"}:
            _corner_schema_engine = DB_engine
            return
        corner_metadata.create_all(
            DB_engine,
            tables=[cafe_corners_table, cafe_corner_members_table, corner_invitations_table]
        )
        _corner_schema_engine = DB_engine


def fetch_corners_for_explore():
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT cafeCorners.cornerID, cafeCorners.cornerName, cafeCorners.cornerDescription,
                   cafeCorners.cornerBanner, cafeCorners.cornerURLEnabled, cafeCorners.cornerURL,
                   accounts.username AS creatorUsername,
                   COALESCE(memberCounts.memberCount, 0) AS memberCount
            FROM cafeCorners
            JOIN accounts ON cafeCorners.userID = accounts.userID
            LEFT JOIN (
                SELECT cornerID, COUNT(userID) AS memberCount
                FROM cafeCornerMembers
                GROUP BY cornerID
            ) AS memberCounts ON memberCounts.cornerID = cafeCorners.cornerID
            ORDER BY cafeCorners.creationDate DESC, cafeCorners.cornerID DESC
        """))
        return _canonicalize_mappings(result)


def fetch_corners_for_user(userID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT cafeCorners.cornerID, cafeCorners.cornerName, cafeCorners.cornerDescription,
                   cafeCorners.cornerBanner, cafeCorners.cornerURLEnabled, cafeCorners.cornerURL,
                   accounts.username AS creatorUsername,
                   COALESCE(memberCounts.memberCount, 0) AS memberCount
            FROM cafeCornerMembers AS userMembers
            JOIN cafeCorners ON userMembers.cornerID = cafeCorners.cornerID
            JOIN accounts ON cafeCorners.userID = accounts.userID
            LEFT JOIN (
                SELECT cornerID, COUNT(userID) AS memberCount
                FROM cafeCornerMembers
                GROUP BY cornerID
            ) AS memberCounts ON memberCounts.cornerID = cafeCorners.cornerID
            WHERE userMembers.userID = :userID
            ORDER BY cafeCorners.creationDate DESC, cafeCorners.cornerID DESC
        """), {"userID": userID})
        return _canonicalize_mappings(result)


def fetch_corner_card_members(cornerIDs):
    if not cornerIDs:
        return {}

    initialize_corner_schema()
    role_column = _quote_identifier("role")
    with connect_to_database() as conn:
        result = conn.execute(text(f"""
            SELECT cafeCornerMembers.cornerID, accounts.userID, accounts.username,
                   profiles.profilePicture, profileColorSets.profilePictureBorderColor
            FROM cafeCornerMembers
            JOIN accounts ON cafeCornerMembers.userID = accounts.userID
            LEFT JOIN profiles ON profiles.userID = accounts.userID
            LEFT JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
            WHERE cafeCornerMembers.cornerID IN :cornerIDs
            ORDER BY cafeCornerMembers.cornerID,
                     CASE WHEN cafeCornerMembers.{role_column} = 'Creator' THEN 0 ELSE 1 END,
                     LOWER(accounts.username)
        """).bindparams(bindparam("cornerIDs", expanding=True)),
            {"cornerIDs": cornerIDs})
        membersByCorner = {cornerID: [] for cornerID in cornerIDs}
        for member in result.mappings():
            member = _canonicalize_mapping(member)
            members = membersByCorner[member["cornerID"]]
            if len(members) < 4:
                members.append(member)
        return membersByCorner


def fetch_corner_by_id(cornerID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT cafeCorners.*, accounts.username AS creatorUsername,
                   COALESCE(memberCounts.memberCount, 0) AS memberCount
            FROM cafeCorners
            JOIN accounts ON cafeCorners.userID = accounts.userID
            LEFT JOIN (
                SELECT cornerID, COUNT(userID) AS memberCount
                FROM cafeCornerMembers
                GROUP BY cornerID
            ) AS memberCounts ON memberCounts.cornerID = cafeCorners.cornerID
            WHERE cafeCorners.cornerID = :cornerID
        """), {"cornerID": cornerID})
        row = result.mappings().first()
        return _canonicalize_mapping(row) if row else None


def fetch_corner_by_url(cornerURL):
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT cafeCorners.*, accounts.username AS creatorUsername,
                   COALESCE(memberCounts.memberCount, 0) AS memberCount
            FROM cafeCorners
            JOIN accounts ON cafeCorners.userID = accounts.userID
            LEFT JOIN (
                SELECT cornerID, COUNT(userID) AS memberCount
                FROM cafeCornerMembers
                GROUP BY cornerID
            ) AS memberCounts ON memberCounts.cornerID = cafeCorners.cornerID
            WHERE cafeCorners.cornerURLEnabled = 1
              AND LOWER(cafeCorners.cornerURL) = LOWER(:cornerURL)
        """), {"cornerURL": cornerURL})
        row = result.mappings().first()
        return _canonicalize_mapping(row) if row else None


def fetch_corner_members(cornerID):
    initialize_corner_schema()
    role_column = _quote_identifier("role")
    with connect_to_database() as conn:
        result = conn.execute(text(f"""
            SELECT accounts.userID, accounts.username, profiles.profilePicture,
                   profileColorSets.profilePictureBorderColor,
                   profiles.channelURLEnabled, profiles.channelURL,
                   cafeCornerMembers.{role_column},
                   cafeCornerMembers.joinedDate
            FROM cafeCornerMembers
            JOIN accounts ON cafeCornerMembers.userID = accounts.userID
            LEFT JOIN profiles ON profiles.userID = accounts.userID
            LEFT JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
            WHERE cafeCornerMembers.cornerID = :cornerID
            ORDER BY CASE WHEN cafeCornerMembers.{role_column} = 'Creator' THEN 0 ELSE 1 END,
                     LOWER(accounts.username)
        """), {"cornerID": cornerID})
        return _canonicalize_mappings(result)


def create_corner(userID, cornerName, cornerDescription, cornerURLEnabled, cornerURL):
    initialize_corner_schema()
    with connect_to_database() as conn:
        with conn.begin():
            if cornerURLEnabled:
                existingURL = conn.execute(text("""
                    SELECT cornerID FROM cafeCorners
                    WHERE cornerURLEnabled = 1 AND LOWER(cornerURL) = LOWER(:cornerURL)
                """), {"cornerURL": cornerURL}).first()
                if existingURL:
                    return None

            result = conn.execute(cafe_corners_table.insert().values({
                "userID": userID,
                "cornerName": cornerName,
                "cornerDescription": cornerDescription,
                "cornerURLEnabled": int(cornerURLEnabled),
                "cornerURL": cornerURL if cornerURLEnabled else None,
                "creationDate": int(time.time())
            }))
            cornerID = result.inserted_primary_key[0]
            role_column = _quote_identifier("role")
            conn.execute(text(f"""
                INSERT INTO cafeCornerMembers (cornerID, userID, {role_column}, joinedDate)
                VALUES (:cornerID, :userID, 'Creator', :joinedDate)
            """),
                {"cornerID": cornerID, "userID": userID, "joinedDate": int(time.time())})
            return cornerID


def fetch_corner_owner(cornerID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT userID FROM cafeCorners WHERE cornerID = :cornerID
        """), {"cornerID": cornerID})
        row = result.first()
        return row[0] if row else None


def create_corner_invitation(cornerID, inviterUserID, invitedUsername):
    initialize_corner_schema()
    with connect_to_database() as conn:
        with conn.begin():
            corner = conn.execute(text("""
                SELECT cornerName, userID FROM cafeCorners WHERE cornerID = :cornerID
            """), {"cornerID": cornerID}).first()
            if not corner or corner[1] != inviterUserID:
                return "not_owner"

            invitee = conn.execute(text("""
                SELECT userID, accountStanding FROM accounts
                WHERE username = :username
            """), {"username": invitedUsername}).first()
            if not invitee or invitee[1] == "Suspended":
                return "user_not_found"
            invitedUserID = invitee[0]
            if invitedUserID == inviterUserID:
                return "already_member"

            membership = conn.execute(text("""
                SELECT 1 FROM cafeCornerMembers
                WHERE cornerID = :cornerID AND userID = :userID
            """), {"cornerID": cornerID, "userID": invitedUserID}).first()
            if membership:
                return "already_member"

            pending = conn.execute(text("""
                SELECT 1 FROM cornerInvitations
                WHERE cornerID = :cornerID AND invitedUserID = :userID
                  AND invitationStatus = 'pending'
            """), {"cornerID": cornerID, "userID": invitedUserID}).first()
            if pending:
                return "already_invited"

            inviterUsername = conn.execute(text("""
                SELECT username FROM accounts WHERE userID = :userID
            """), {"userID": inviterUserID}).scalar_one()
            conn.execute(text("""
                INSERT INTO cornerInvitations
                    (cornerID, inviterUserID, invitedUserID, invitationStatus, createdAt)
                VALUES (:cornerID, :inviterUserID, :invitedUserID, 'pending', :createdAt)
            """), {
                "cornerID": cornerID,
                "inviterUserID": inviterUserID,
                "invitedUserID": invitedUserID,
                "createdAt": int(time.time())
            })
            conn.execute(text("""
                INSERT INTO notifications
                    (notificationRecipientID, notificationSenderID, notificationTitle,
                     notificationDescription, notificationDateTime, notificationItem,
                     notificationImage, notificationRead)
                VALUES (:recipientID, :senderID, :title, :description, :createdAt,
                        :item, 'None', 0)
            """), {
                "recipientID": invitedUserID,
                "senderID": inviterUserID,
                "title": "Corner invitation",
                "description": f"{inviterUsername} invited you to join {corner[0]}",
                "createdAt": int(time.time()),
                "item": f"corner-invite:{cornerID}"
            })
            return "invited"


def fetch_pending_corner_invitations(userID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT cornerInvitations.cornerID, cafeCorners.cornerName,
                   inviter.username AS inviterUsername, inviterProfile.profilePicture,
                   inviterColors.profilePictureBorderColor
            FROM cornerInvitations
            JOIN cafeCorners ON cafeCorners.cornerID = cornerInvitations.cornerID
            JOIN accounts AS inviter ON inviter.userID = cornerInvitations.inviterUserID
            LEFT JOIN profiles AS inviterProfile ON inviterProfile.userID = inviter.userID
            LEFT JOIN profileColorSets AS inviterColors
                ON inviterProfile.profileColorTheme = inviterColors.profileSetID
            WHERE cornerInvitations.invitedUserID = :userID
              AND cornerInvitations.invitationStatus = 'pending'
            ORDER BY cornerInvitations.createdAt DESC, cornerInvitations.invitationID DESC
        """), {"userID": userID})
        return _canonicalize_mappings(result)


def accept_corner_invitation(userID, cornerID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        with conn.begin():
            invitation = conn.execute(text("""
                SELECT invitationID FROM cornerInvitations
                WHERE cornerID = :cornerID AND invitedUserID = :userID
                  AND invitationStatus = 'pending'
                ORDER BY invitationID DESC
            """), {"cornerID": cornerID, "userID": userID}).first()
            if not invitation:
                return False

            membership = conn.execute(text("""
                SELECT 1 FROM cafeCornerMembers
                WHERE cornerID = :cornerID AND userID = :userID
            """), {"cornerID": cornerID, "userID": userID}).first()
            if not membership:
                role_column = _quote_identifier("role")
                conn.execute(text(f"""
                    INSERT INTO cafeCornerMembers (cornerID, userID, {role_column}, joinedDate)
                    VALUES (:cornerID, :userID, 'Member', :joinedDate)
                """), {"cornerID": cornerID, "userID": userID, "joinedDate": int(time.time())})
            conn.execute(text("""
                UPDATE cornerInvitations SET invitationStatus = 'accepted'
                WHERE cornerID = :cornerID AND invitedUserID = :userID
                  AND invitationStatus = 'pending'
            """), {"cornerID": cornerID, "userID": userID})
            conn.execute(text("""
                UPDATE notifications SET notificationRead = 1
                WHERE notificationRecipientID = :userID AND notificationItem = :item
            """), {"userID": userID, "item": f"corner-invite:{cornerID}"})
            return True


def decline_corner_invitation(userID, cornerID):
    initialize_corner_schema()
    with connect_to_database() as conn:
        with conn.begin():
            result = conn.execute(text("""
                UPDATE cornerInvitations SET invitationStatus = 'declined'
                WHERE cornerID = :cornerID AND invitedUserID = :userID
                  AND invitationStatus = 'pending'
            """), {"cornerID": cornerID, "userID": userID})
            if result.rowcount:
                conn.execute(text("""
                    UPDATE notifications SET notificationRead = 1
                    WHERE notificationRecipientID = :userID AND notificationItem = :item
                """), {"userID": userID, "item": f"corner-invite:{cornerID}"})
            return result.rowcount > 0


def fetch_admin_accounts():
    """Fetch account details, profile pictures, standings, and assigned role names."""
    with connect_to_database() as conn:
        accounts = conn.execute(text("""
            SELECT accounts.userID, accounts.username, accounts.accountStanding,
                   profiles.profilePicture, profileColorSets.profilePictureBorderColor
            FROM accounts
            LEFT JOIN profiles ON profiles.userID = accounts.userID
            LEFT JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
            ORDER BY LOWER(accounts.username)
        """))
        accounts = _canonicalize_mappings(accounts)
        roles = conn.execute(text("""
            SELECT user_roles.userID, roles.roleName
            FROM user_roles
            JOIN roles ON user_roles.roleID = roles.roleID
            ORDER BY user_roles.userID, roles.roleID
        """)).fetchall()
        roleNamesByUser = {}
        for userID, roleName in roles:
            roleNamesByUser.setdefault(userID, []).append(roleName)

        return [
            {
                **dict(account),
                "roleNames": ", ".join(roleNamesByUser.get(account["userID"], []))
            }
            for account in accounts
        ]


def suspend_user_account(userID):
    """Suspend an account if it exists and is not already suspended."""
    with connect_to_database() as conn:
        with conn.begin():
            result = conn.execute(text("""
                UPDATE accounts
                SET accountStanding = 'Suspended'
                WHERE userID = :userID AND accountStanding != 'Suspended'
            """), {"userID": userID})
            return result.rowcount > 0


def createAccount(username, hashed_password):
    conn = connect_to_database()

    try:
        # Insert the account information for the newly created user account
        conn.execute(text("""INSERT INTO accounts 
                            (username, password, accountStanding, verification)
                            VALUES (:username, :password, :accountStanding, :verification)"""),
                     {
                         "username": username,
                         "password": hashed_password,
                         "accountStanding": "Active",
                         "verification": "None"
                     }
                     )
        conn.commit()
        # Fetch the userID of that newly created account to use for more inserts
        result = conn.execute(text("""SELECT userID 
                                      FROM accounts 
                                      WHERE username = :username"""),
                              {"username": username})
        userID = result.fetchone()
        joinDate = datetime.today()
        formatted_joinDate = joinDate.strftime("%d/%m/%Y")
        # Create the profile for the user account
        conn.execute(text("""INSERT INTO profiles 
                            (userID, joinDate, profileColorTheme, channelURLEnabled, channelURL)
                            VALUES (:userID, :joinDate, :profileColorTheme, :channelURLEnabled, :channelURL)"""),
                     {
                         "userID": userID[0],
                         "joinDate": formatted_joinDate,
                         "profileColorTheme": 5,
                         "channelURLEnabled": 0,
                         "channelURL": username
                     }
                     )
        conn.commit()
        # Create the saved videos playlist for the user account
        conn.execute(text("""INSERT INTO playlists 
                            (userID, playlistName, playlistType, visibilityType) 
                            VALUES (:userID, :playlistName, :playlistType, :visibilityType)"""),
                     {
                         "userID": userID[0],
                         "playlistName": f"{username}'s Saved Videos",
                         "playlistType": "watch_queue",
                         "visibilityType": "Private"
                     }
                     )
        conn.commit()
        print("Account created")
        return True, "Account created successfully!"  # Return success message
    except IntegrityError:
        return False, "Username already exists"  # Return error message
    finally:
        conn.close()


def changeAccountDetailsConfirm(userID, username, channelURL):
    """This is for changing account details e.g. username, channel URL, etc"""
    conn = connect_to_database()

    try:
        conn.execute(text("""UPDATE accounts 
                             SET username = :username 
                             WHERE userID = :userID"""),
                     {
                         "username": username,
                         "userID": userID
                     }
                     )
        conn.commit()
        # Check if channelURL is enabled
        result = conn.execute(text("""SELECT channelURLEnabled 
                                      FROM profiles 
                                      WHERE userID = :userID"""),
                              {
                                  "userID": userID
                              }
                              )
        channelURLStatus = result.fetchone()
        print(channelURLStatus[0])
        # Check if new channelURL does not already exist
        result = conn.execute(text("""SELECT channelURL 
                                      FROM profiles 
                                      WHERE UPPER(channelURL) = UPPER(:channelURL)"""),
                              {
                                  "channelURL": channelURL
                              }
                              )
        channelURLExist = result.fetchone()
        print(channelURLExist)
        # If the channelURL does not exist then update the user's channelURL
        if not channelURLExist:
            conn.execute(text("""UPDATE profiles 
                                 SET channelURL = :channelURL 
                                 WHERE userID = :userID"""),
                         {
                             "channelURL": channelURL,
                             "userID": userID
                         }
                         )
            conn.commit()
            # Enable channelURL if its not enabled
            if channelURLStatus[0] == 0:
                conn.execute(text("""UPDATE profiles 
                                     SET channelURLEnabled = :channelURLEnabled 
                                     WHERE userID = :userID"""),
                             {
                                 "channelURLEnabled": 1,
                                 "userID": userID
                             }
                             )
                conn.commit()
        else:
            print(f"Channel URL, {channelURLExist}, already exists")
            # If the channelURL does exist and the channelURL is not enabled
            if channelURLStatus[0] == 0:
                result = conn.execute(text("""SELECT * 
                                          FROM profiles 
                                          WHERE UPPER(channelURL) = UPPER(:channelURL) AND userID = :userID"""),
                                      {
                                          "channelURL": channelURL,
                                          "userID": userID
                                      }
                                      )
                # Check if the channelURL matches the userID of the user saving the changes
                channelURL_Matches_UserID = result.fetchone()
                # Enable channelURL if its not enabled
                if channelURL_Matches_UserID:
                    conn.execute(text("""UPDATE profiles 
                                              SET channelURLEnabled = :channelURLEnabled 
                                              WHERE userID = :userID"""),
                                 {
                                     "channelURLEnabled": 1,
                                     "userID": userID
                                 }
                                 )
                    conn.commit()
        return True, "Account details updated successfully"
    except IntegrityError:
        return False, "Account details failed to update"
    finally:
        conn.close()


def fetch_season_state():
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM season"))
    seasonState = result.fetchone()

    if seasonState[0] == 1:
        result = conn.execute(text("""SELECT * 
                                      FROM events 
                                      WHERE eventID = :eventID"""),
                              {"eventID": seasonState[1]
                               }
                              )
        event_data = result.fetchone()

        conn.close()

        return event_data, seasonState[0]
    else:
        conn.close()
        return "None", seasonState[0]


def fetch_explore_trending_feed():
    """Fetches the trending feed for the explore page"""
    conn = connect_to_database()

    result = conn.execute(text("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                profileColorSets.profilePictureBorderColor, profiles.channelURLEnabled, profiles.channelURL
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                JOIN profiles ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE accountStanding != 'Suspended'
                                ORDER BY views DESC  -- Shows newest first
                                LIMIT 12
                                """))

    trending_videos = result.fetchall()

    conn.close()

    return trending_videos


def login_auth_check(username):
    """Checks if the username submitted exists in the database"""
    conn = connect_to_database()

    result = conn.execute(text('SELECT * FROM accounts WHERE username = :username'), {"username": username})
    user = result.mappings().fetchone()

    conn.close()

    return _canonicalize_mapping(user) if user else None


def fetch_video_view_count_for_watch_page(videoID):
    """Returns the view count for the queried video on the watch page"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT views FROM videos WHERE videoID = :videoID"), {"videoID": videoID})
    viewCount = result.fetchone()[0]

    conn.close()

    return viewCount


def update_video_view_count(viewUpdate, videoID):
    """Updates the view count for the queried video on the watch page"""
    conn = connect_to_database()

    conn.execute(text("UPDATE videos SET views = :viewCount WHERE videoID = :videoID"),
                 {"viewCount": viewUpdate, "videoID": videoID})
    conn.commit()
    conn.close()


def fetch_username(userID):
    """Fetches the username for the queried userID"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT username FROM accounts WHERE userID = :userID"), {"userID": userID})
    username = result.fetchone()

    conn.close()

    return username


def fetch_subscribers_count_from_creator(creatorID):
    """Fetches the subscribers count from the creator of the queried video"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM subscriptions WHERE subscribedToUserID = :creatorID"),
                          {"creatorID": creatorID})
    subscribers = result.fetchall()

    conn.close()

    return subscribers


def check_user_subscribed_to_creator_channel(userID, creatorID):
    """Determines if the user is subscribed to the creator of the queried video"""
    conn = connect_to_database()

    result = conn.execute(
        text("SELECT * FROM subscriptions WHERE userID = :userID AND subscribedToUserID = :creatorID"),
        {"userID": userID, "creatorID": creatorID})
    isSubscribedToChannel = result.fetchone()

    conn.close()

    return isSubscribedToChannel


def fetch_video_likes_for_watch_page(videoID):
    """Fetches the likes count for the queried video"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM likedVideos WHERE videoID = :videoID"), {"videoID": videoID})
    likes = result.fetchall()

    conn.close()

    return likes


def check_user_liked_video(videoID, userID):
    """Check if the user has liked the queried video"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM likedVideos WHERE videoID = :videoID AND userID = :userID"),
                          {"videoID": videoID, "userID": userID})
    isLikedVideo = result.fetchone()

    conn.close()

    return isLikedVideo


def fetch_user_playlists(userID):
    """Fetches the user's playlists"""
    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT playlists.playlistID, playlists.userID, playlists.playlistName, playlists.playlistType, 
                    playlists.visibilityType, accounts.username, profiles.profilePicture, 
                    profileColorSets.profilePictureBorderColor,
                    (SELECT COUNT(*) FROM playlist_contents
                     WHERE playlist_contents.playlistID = playlists.playlistID) AS videoCount
                    FROM playlists
                    JOIN accounts ON playlists.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    WHERE playlists.userID = :userID AND playlists.playlistType != 'watch_queue'
                    ORDER BY playlists.playlistID DESC
                    """), {"userID": userID})
    userPlaylists = result.fetchall()

    conn.close()

    return userPlaylists


def validate_userID(userID):
    """Checks if the userID exists on the database"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM accounts WHERE userID = :userID"), {"userID": userID})
    foundUserID = result.fetchone()

    conn.close()

    return foundUserID


def check_channelURL_status(channelURL):
    """Check if the profile's user status"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT channelURLEnabled FROM profiles WHERE channelURL = :channelURL"),
                          {"channelURL": channelURL})
    channelURLEnabled = result.fetchone()

    conn.close()

    return channelURLEnabled


def fetch_profile_from_channelURL(channelURL):
    """Fetches the profile from the given channel URL"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT userID FROM profiles WHERE channelURL = :channelURL"),
                          {"channelURL": channelURL})
    userID = result.fetchone()

    conn.close()

    return userID


def remove_user_subscription(userID, creatorID):
    """Removes the queried creator channel from the user's subscriptions"""

    conn = connect_to_database()

    conn.execute(text("DELETE FROM subscriptions WHERE userID = :userID AND subscribedToUserID = :creatorID"),
                 {"userID": userID, "creatorID": creatorID})
    conn.commit()

    conn.close()


def add_user_subscription(userID, creatorID):
    """Adds the queried creator channels to the user's subscriptions"""

    conn = connect_to_database()

    conn.execute(text("INSERT INTO subscriptions (userID, subscribedToUserID) VALUES (:userID, :creatorID)"),
                 {"userID": userID, "creatorID": creatorID})
    conn.commit()

    conn.close()


def check_video_exists(videoID):
    """Checks if the queried videoID exists on the database"""

    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM videos WHERE videoID = :videoID"),
                          {"videoID": videoID})
    videoExists = result.fetchone()

    conn.close()

    return videoExists


def check_video_liked(videoID, creatorID, userID):
    """Check if the user liked the queried video"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                  FROM likedVideos 
                                  WHERE videoID = :videoID AND creatorID = :creatorID AND userID = :userID"""),
                          {"videoID": videoID, "creatorID": creatorID, "userID": userID})
    isLikedVideo = result.fetchone()

    conn.close()

    return isLikedVideo


def delete_like_from_video(videoID, creatorID, userID):
    """Deletes the user's like from the queried video"""

    conn = connect_to_database()

    conn.execute(
        text("DELETE FROM likedVideos WHERE videoID = :videoID AND creatorID = :creatorID AND userID = :userID"),
        {"videoID": videoID, "creatorID": creatorID, "userID": userID})
    conn.commit()

    conn.close()


def add_like_to_video(videoID, creatorID, userID):
    """Adds the user's like to the queried video"""

    conn = connect_to_database()

    conn.execute(text("INSERT INTO likedVideos (videoID, creatorID, userID) VALUES (:videoID, :creatorID, :userID)"),
                 {"videoID": videoID, "creatorID": creatorID, "userID": userID})
    conn.commit()

    conn.close()


def fetch_video_title(videoID):
    """Fetches the video title from the queried video"""

    conn = connect_to_database()

    result = conn.execute(text("SELECT videoTitle FROM videos WHERE videoID = :videoID"),
                          {"videoID": videoID})
    videoTitle = result.fetchone()

    conn.close()

    return videoTitle


def fetch_video_comment(commentID):
    """Checks if the queried comment exists on the database"""

    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM comments WHERE commentID = :commentID"), {"commentID": commentID})
    commentExists = result.fetchone()

    conn.close()

    return commentExists


def check_comment_liked(commentID, commenterID, userID):
    """Checks if the queried comment is liked by the user"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                  FROM likedComments 
                                  WHERE commentID = :commentID AND commenterID = :commenterID AND userID = :userID"""),
                          {"commentID": commentID, "commenterID": commenterID, "userID": userID})
    isLikedComment = result.fetchone()

    conn.close()

    return isLikedComment


def delete_comment_like(commentID, commenterID, userID):
    """Deletes the user's like from the queried comment"""

    conn = connect_to_database()

    conn.execute(text("""DELETE FROM likedComments 
                         WHERE commentID = :commentID AND commenterID = :commenterID AND userID = :userID"""),
                 {"commentID": commentID, "commenterID": commenterID, "userID": userID})
    conn.commit()

    conn.close()


def add_comment_like(commentID, commenterID, userID):
    """Adds the user's like to the queried comment"""

    conn = connect_to_database()

    conn.execute(text("""INSERT INTO likedComments (commentID, commenterID, userID) 
                         VALUES (:commentID, :commenterID, :userID)"""),
                 {"commentID": commentID, "commenterID": commenterID, "userID": userID})
    conn.commit()

    conn.close()


def fetch_video_reply(replyID):
    """Checks if the queried reply exists on the database"""

    conn = connect_to_database()

    result = conn.execute(text("SELECT * FROM replies WHERE replyID = :replyID"), {"replyID": replyID})
    replyExists = result.fetchone()

    conn.close()

    return replyExists


def check_reply_liked(replyID, replierID, userID):
    """Checks if the queried reply is liked by the user"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                  FROM likedReplies 
                                  WHERE replyID = :replyID AND replierID = :replierID AND userID = :userID"""),
                          {"replyID": replyID, "replierID": replierID, "userID": userID})
    isLikedReply = result.fetchone()

    conn.close()

    return isLikedReply


def delete_reply_like(replyID, replierID, userID):
    """Deletes the user's like from the queried reply"""

    conn = connect_to_database()

    conn.execute(text("""DELETE FROM likedReplies 
                         WHERE replyID = :replyID AND replierID = :replierID AND userID = :userID"""),
                 {"replyID": replyID, "replierID": replierID, "userID": userID})
    conn.commit()

    conn.close()


def add_reply_like(replyID, replierID, userID):
    """Adds the user's like to the queried reply"""

    conn = connect_to_database()

    conn.execute(text("INSERT INTO likedReplies (replyID, replierID, userID) VALUES (:replyID, :replierID, :userID)"),
                 {"replyID": replyID, "replierID": replierID, "userID": userID})
    conn.commit()

    conn.close()


def fetch_profile_color_sets():
    """Fetches the profile color sets for the edit profile page"""

    conn = connect_to_database()

    result = conn.execute(text('SELECT profileSetID, profileSetName FROM profileColorSets'))
    profileColorSets = result.fetchall()

    conn.close()

    return profileColorSets


def fetch_user_feature_access(userID):
    """Checks if the user has feature access"""

    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT * 
                    FROM feature_access
                    WHERE userID = :userID
                    """),
                          {"userID": userID})
    userAccessList = result.fetchall()

    conn.close()

    return userAccessList


def fetch_user_features(featureID):
    """Fetches the features the user has access to"""

    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT *
                    FROM feature_gating
                    WHERE featureID = :featureID
                    """),
                          {"featureID": featureID})
    feature = result.fetchone()

    conn.close()

    return feature


def fetch_user_liked_videos(userID):
    """Fetches the user's liked videos from the database"""

    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                    profileColorSets.profilePictureBorderColor, accounts.accountStanding
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    JOIN likedVideos ON likedVideos.videoID = videos.videoID
                    WHERE likedVideos.userID = :userID AND accountStanding != 'Suspended'
                    ORDER BY videos.videoID DESC  -- Shows newest first
                    """), {"userID": userID})
    videos = result.fetchall()

    conn.close()

    return videos


def create_video_playlist(userID, playlistName, playlistDescription, playlistType, playlistVisibility):
    """Inserts the submitted user playlist into the database"""

    conn = connect_to_database()

    conn.execute(text("""INSERT INTO playlists (userID, playlistName, playlistDescription, playlistType, visibilityType) 
                         VALUES (:userID, :playlistName, :playlistDescription, :playlistType, :playlistVisibility)"""),
                 {"userID": userID, "playlistName": playlistName, "playlistDescription": playlistDescription,
                  "playlistType": playlistType, "playlistVisibility": playlistVisibility})
    conn.commit()

    conn.close()


def fetch_user_playlist(playlistID):
    """Fetches the queried user playlist"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                  FROM playlists WHERE playlistID = :playlistID AND playlistType != 'watch_queue' """),
                          {"playlistID": playlistID})
    playlistIDFound = result.fetchone()

    conn.close()

    return playlistIDFound


def fetch_user_playlist_videos(playlistID):
    """Fetches the videos for the user playlist"""

    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                    profileColorSets.profilePictureBorderColor, accounts.accountStanding
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    JOIN playlist_contents ON playlist_contents.videoID = videos.videoID
                    WHERE playlist_contents.playlistID = :playlistID AND accounts.accountStanding != 'Suspended'
                    ORDER BY playlist_contents.videoID DESC  -- Shows newest first
                    """),
                          {"playlistID": playlistID})
    videos = result.fetchall()

    conn.close()

    return videos


def fetch_user_saves_playlist(userID, playlistType):
    """Fetches the user's saved videos playlist"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * FROM playlists WHERE userID = :userID AND playlistType = :playlistType"""),
                          {"userID": userID, "playlistType": playlistType})
    playlistIDFound = result.fetchone()

    conn.close()

    return playlistIDFound


def fetch_user_saved_videos(playlistID):
    """Fetches the videos from the user's saved videos playlist"""

    conn = connect_to_database()

    result = conn.execute(text("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                    profileColorSets.profilePictureBorderColor, accounts.accountStanding
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    JOIN playlist_contents ON playlist_contents.videoID = videos.videoID
                    WHERE playlist_contents.playlistID = :playlistID AND accountStanding != 'Suspended'
                    ORDER BY playlist_contents.videoID DESC  -- Shows newest first
                    """),
                          {"playlistID": playlistID})
    videos = result.fetchall()

    conn.close()

    return videos


def uploadVideoToDatabase(userID, title, description, videoTags, filename, thumbnailFilename):
    """Uploads the video's information to the database"""

    conn = connect_to_database()

    datetimeOfPublishedVideo = int(time.time())

    try:
        conn.execute(text("""INSERT INTO videos (userID, videoTitle, videoDescription, videoTags, videoFile,
                                videoThumbnail, datetime, views) VALUES (:userID, :videoTitle, :videoDescription,
                                :videoTags, :videoFile, :videoThumbnail, :datetime, 0)"""),
                     {"userID": userID, "videoTitle": title, "videoDescription": description, "videoTags":
                         videoTags, "videoFile": filename, "videoThumbnail": thumbnailFilename,
                      "datetime": datetimeOfPublishedVideo})
        conn.commit()
        print("Video uploaded")
        return True, "Video uploaded successfully"
    except IntegrityError:
        return False, "Video failed to upload"
    finally:
        conn.close()


def fetch_creator_videos(userID):
    with DB_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT videoID AS video_id, videoTitle AS video_title,
                   videoDescription AS video_description, videoTags AS video_tags,
                   videoFile AS video_file, videoThumbnail AS video_thumbnail,
                   datetime AS uploaded_at, views
            FROM videos
            WHERE userID = :userID
            ORDER BY datetime DESC, videoID DESC
        """), {"userID": userID})
        return [dict(row) for row in result.mappings()]


def update_creator_video(userID, videoID, title, description, videoTags, thumbnailFilename=None):
    with DB_engine.begin() as conn:
        result = conn.execute(
            text("""
                SELECT videoThumbnail AS video_thumbnail
                FROM videos
                WHERE videoID = :videoID AND userID = :userID
            """),
            {"videoID": videoID, "userID": userID}
        )
        video = result.mappings().first()
        if video is None:
            return None

        conn.execute(text("""
            UPDATE videos
            SET videoTitle = :title,
                videoDescription = :description,
                videoTags = :videoTags,
                videoThumbnail = COALESCE(:thumbnailFilename, videoThumbnail)
            WHERE videoID = :videoID AND userID = :userID
        """), {
            "title": title,
            "description": description,
            "videoTags": videoTags,
            "thumbnailFilename": thumbnailFilename,
            "videoID": videoID,
            "userID": userID,
        })
        return video["video_thumbnail"]


def delete_creator_video(userID, videoID):
    with DB_engine.begin() as conn:
        result = conn.execute(text("""
            SELECT videoFile AS video_file, videoThumbnail AS video_thumbnail
            FROM videos
            WHERE videoID = :videoID AND userID = :userID
        """), {"videoID": videoID, "userID": userID})
        video = result.mappings().first()
        if video is None:
            return None

        conn.execute(text("""
            DELETE FROM likedReplies
            WHERE replyID IN (
                SELECT replyID FROM replies
                WHERE commentID IN (SELECT commentID FROM comments WHERE videoID = :videoID)
            )
        """), {"videoID": videoID})
        conn.execute(text("""
            DELETE FROM likedComments
            WHERE commentID IN (SELECT commentID FROM comments WHERE videoID = :videoID)
        """), {"videoID": videoID})
        conn.execute(text("""
            DELETE FROM replies
            WHERE commentID IN (SELECT commentID FROM comments WHERE videoID = :videoID)
        """), {"videoID": videoID})
        conn.execute(text("DELETE FROM comments WHERE videoID = :videoID"), {"videoID": videoID})
        conn.execute(text("DELETE FROM playlist_contents WHERE videoID = :videoID"), {"videoID": videoID})
        conn.execute(text("DELETE FROM likedVideos WHERE videoID = :videoID"), {"videoID": videoID})
        conn.execute(text("DELETE FROM watchHistory WHERE videoID = :videoID"), {"videoID": videoID})
        conn.execute(
            text("DELETE FROM videos WHERE videoID = :videoID AND userID = :userID"),
            {"videoID": videoID, "userID": userID}
        )

        videoFile = video["video_file"]
        videoThumbnail = video["video_thumbnail"]
        videoFileReferenced = conn.execute(
            text("SELECT COUNT(*) FROM videos WHERE videoFile = :filename"),
            {"filename": videoFile}
        ).scalar_one() > 0
        videoThumbnailReferenced = conn.execute(
            text("SELECT COUNT(*) FROM videos WHERE videoThumbnail = :filename"),
            {"filename": videoThumbnail}
        ).scalar_one() > 0
        return {
            "videoFile": videoFile,
            "videoThumbnail": videoThumbnail,
            "videoFileReferenced": videoFileReferenced,
            "videoThumbnailReferenced": videoThumbnailReferenced,
        }


def video_media_is_referenced(column, filename):
    if column not in {"videoFile", "videoThumbnail"}:
        raise ValueError("Unsupported video media column")
    with DB_engine.connect() as conn:
        return conn.execute(
            text(f"SELECT COUNT(*) FROM videos WHERE {column} = :filename"),
            {"filename": filename}
        ).scalar_one() > 0


def sendCommentToDatabase(videoID, userID, comment):
    """Sends the comment to the database"""

    conn = connect_to_database()

    try:
        conn.execute(text("INSERT INTO comments (videoID, userID, comment) VALUES (:videoID, :userID, :comment)"),
                     {"videoID": videoID, "userID": userID, "comment": comment})
        conn.commit()

        # Send the notification to the database

        usernameOfCommenter = fetch_username(userID)
        print(usernameOfCommenter[0])
        result = conn.execute(text("SELECT userID FROM videos WHERE videoID = :videoID"), {"videoID": videoID})
        creatorID = result.fetchone()

        if int(userID) != int(creatorID[0]):
            sendNotificationToDatabase(creatorID[0], userID, f"{usernameOfCommenter[0]} has commented on your video",
                                       "", "commentOnVideo", "None")

        print("Comment sent")
    except IntegrityError:
        print("Error with posting comment")
    finally:
        conn.close()


def sendReplyToDatabase(commentID, userID, reply):
    """Sends the reply to the database"""

    conn = connect_to_database()

    try:
        conn.execute(text("INSERT INTO replies (commentID, userID, reply) VALUES (:commentID, :userID, :reply)"),
                     {"commentID": commentID, "userID": userID, "reply": reply})
        conn.commit()
        print("Reply sent")
    except IntegrityError:
        print("Error with posting reply")
    finally:
        conn.close()


def uploadProfilePictureToDatabase(profilePictureFilename, userID):
    """Uploads the user's submitted profile picture to the database"""

    conn = connect_to_database()

    try:
        conn.execute(text("UPDATE profiles SET profilePicture = :profilePicture WHERE userID = :userID"),
                     {"profilePicture": profilePictureFilename, "userID": userID})
        conn.commit()
        return True, "Uploaded successfully"
    except IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        conn.close()


def uploadProfileBannerToDatabase(profileBannerFilename, userID):
    """Uploads the user's submitted banner to the database"""

    conn = connect_to_database()

    try:
        conn.execute(text("UPDATE profiles SET profileBanner = :profileBanner WHERE userID = :userID"),
                     {"profileBanner": profileBannerFilename, "userID": userID})
        conn.commit()
        return True, "Uploaded successfully"
    except IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        conn.close()


def sendProfileBioToDatabase(bio, userID):
    """Sends the user's submitted profile bio to the database"""

    conn = connect_to_database()

    try:
        conn.execute(text("UPDATE profiles SET profileBio = :profileBio WHERE userID = :userID"),
                     {"profileBio": bio, "userID": userID})
        conn.commit()
        return True, "Uploaded successfully"
    except IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        conn.close()


def updateProfileColorTheme(profileColorTheme, userID):
    """Changes the user's profile color theme"""

    conn = connect_to_database()

    try:
        conn.execute(text('UPDATE profiles SET profileColorTheme = :profileColorTheme WHERE userID = :userID'),
                     {"profileColorTheme": profileColorTheme, "userID": userID})
        conn.commit()
        return True, "Profile Color Theme has been updated"
    except IntegrityError:
        return False, "Profile Color Theme failed to update"
    finally:
        conn.close()


def sendNotificationToDatabase(recipientID, senderID, title, description, item, image):
    """Sends the notification to the database"""

    conn = connect_to_database()

    notificationSent = int(time.time())

    try:
        result = conn.execute(text("""SELECT * 
                                      FROM notifications 
                                      WHERE notificationRecipientID = :recipientID AND notificationSenderID = :senderID 
                                      AND notificationTitle = :title 
                                      AND notificationDescription = :description"""),
                              {"recipientID": recipientID, "senderID": senderID,
                               "title": title, "description": description})
        notificationExists = result.fetchone()

        if notificationExists:
            print("Notification Already Exists")
        else:
            conn.execute(text("""INSERT INTO notifications (notificationRecipientID, notificationSenderID, 
                        notificationTitle, notificationDescription, notificationDateTime, notificationItem, 
                        notificationImage, notificationRead) 
                        VALUES (:RecipientID, :SenderID, :Title, :Description, :DateTime, :Item, :Image, :Read)"""),
                         {"RecipientID": recipientID, "SenderID": senderID, "Title": title,
                          "Description": description, "DateTime": notificationSent, "Item": item, "Image": image,
                          "Read": 0})
            conn.commit()
            print("Notification sent")
    except IntegrityError:
        print("Error with sending notification")
    finally:
        conn.close()


def sendWatchedVideoToDatabase(userID, videoID):
    """Add watched video to the user's watch history on the database"""

    conn = connect_to_database()

    dateOfVideoWatched = int(time.time())

    try:
        result = conn.execute(text("SELECT * FROM watchHistory WHERE userID = :userID AND videoID = :videoID"),
                              {"userID": userID, "videoID": videoID})
        videoWatched = result.fetchone()

        if videoWatched:
            conn.execute(text("""UPDATE watchHistory 
                                     SET historyDateTime = :DateTime 
                                     WHERE userID = :userID AND videoID = :videoID"""),
                         {"DateTime": dateOfVideoWatched, "userID": userID, "videoID": videoID})
            conn.commit()
        else:
            conn.execute(text("""INSERT INTO watchHistory (userID, videoID, historyDateTime) 
                                 VALUES (:userID, :videoID, :DateTime)"""),
                         {"userID": userID, "videoID": videoID, "DateTime": dateOfVideoWatched})
            conn.commit()
    except IntegrityError:
        print("Error when updating watch history")
    finally:
        conn.close()


def mark_notification_as_read(notificationID, userID):
    """Marks the queried notification as read in the database"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * FROM notifications 
                                  WHERE notificationID = :notificationID AND notificationRecipientID = :userID"""),
                          {"notificationID": notificationID, "userID": userID})
    notificationMatch = result.fetchone()

    if notificationMatch:
        conn.execute(text("""UPDATE notifications SET notificationRead = 1 WHERE notificationID = :notificationID"""),
                     {"notificationID": notificationID})
        conn.commit()
    else:
        print("NotificationID and userID mismatch: No changes have been made.")

    conn.close()


def fetch_video_api(videoID):
    """Fetches video data for the API"""

    conn = connect_to_database()

    result = conn.execute(text("""SELECT * 
                                  FROM videos 
                                  WHERE videoID = :videoID"""), {"videoID": videoID})
    video = result.fetchone()
    if not video:
        conn.close()
        return None

    videoCreator = video[1]

    result = conn.execute(text("""SELECT accountStanding 
                         FROM accounts 
                         WHERE userID = :userID"""), {"userID": videoCreator})
    accountStanding = result.fetchone()[0]

    conn.close()

    if accountStanding == "Suspended":
        return None
    else:
        return video


def fetch_user_role(userID):
    """Fetches the roles assigned to the user"""

    with connect_to_database() as conn:
        result = conn.execute(text("""
            SELECT roles.*
            FROM user_roles
            JOIN roles ON user_roles.roleID = roles.roleID
            WHERE user_roles.userID = :userID
            ORDER BY CASE WHEN roles.roleName = 'Admin' THEN 0 ELSE 1 END, roles.roleID
        """), {"userID": userID})
        row = result.mappings().first()
        return _canonicalize_mapping(row) if row else None
