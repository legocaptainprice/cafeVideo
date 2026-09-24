import sqlite3

import config

import random

from collections import Counter

# Set the location for the database
cafeDatabasePath = config.sqlite_db_path


def connect_to_database():
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def fetch_latest_videos():
    """Fetch videos in the database in descending order"""
    conn = connect_to_database()
    cursor = conn.cursor()

    # Fetch the latest videos for the new videos feed
    cursor.execute("""
                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, 
                videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor, 
                profiles.channelURLEnabled, profiles.channelURL, accounts.accountStanding
                FROM videos
                JOIN accounts ON videos.userID = accounts.userID
                JOIN profiles ON profiles.userID = accounts.userID
                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                WHERE accountStanding != 'Suspended'
                ORDER BY videoID DESC  -- Shows newest first
            """)
    videos = cursor.fetchall()

    conn.close()

    return videos


def fetch_profile_info(variant, userID):
    """Fetch the profile of the user from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "minimal":
        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                channelURL
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        conn.close()

        return profilePicture


def fetch_subscription_info(userID):
    """Fetches the user subscriptions from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("""
                            SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                            accounts.username, channelURLEnabled, channelURL, accounts.accountStanding
                            FROM profiles
                            JOIN accounts ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = ? AND accountStanding != 'Suspended' """, (userID,))
    subscriptionsInfo = cursor.fetchall()

    conn.close()

    return subscriptionsInfo


def fetch_subscription_videos(variant, userID):
    """Fetches the user subscription videos from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "latest":
        cursor.execute("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                profileColorSets.profilePictureBorderColor, profiles.channelURLEnabled, profiles.channelURL
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                JOIN profiles ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = ? AND accountStanding != 'Suspended'
                                ORDER BY videoID DESC  -- Shows newest first
                                LIMIT 12
                                """, (userID,))
    if variant == "page":
        # Fetch the latest videos for the subscriptions feed
        cursor.execute("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                            videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, accounts.accountStanding
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = ? AND accountStanding != 'Suspended'
                            ORDER BY videoID DESC  -- Shows newest first
                        """, (userID,))

    subscription_videos = cursor.fetchall()

    conn.close()

    return subscription_videos


def fetch_user_notifications(variant, userID):
    """Fetch user notifications from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "minimal":
        cursor.execute("""
                                SELECT notifications.*, profiles.profilePicture, profileColorSets.profilePictureBorderColor 
                                FROM notifications
                                JOIN profiles ON notifications.notificationSenderID = profiles.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE notificationRecipientID = ?
                                ORDER BY notificationDateTime DESC
                                         """,
                       (userID,))
        notifications = cursor.fetchall()

        conn.close()

        return notifications


def fetch_account_info(variant, userID):
    """Fetch the user account info from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "feature_access":
        cursor.execute("""
                                SELECT feature_access.featureID, feature_gating.featureName
                                FROM feature_access
                                JOIN feature_gating ON feature_access.featureID = feature_gating.featureID
                                JOIN accounts ON feature_access.userID = accounts.userID
                                WHERE accounts.userID = ?  
                                """, (userID,))
        featureAccess = cursor.fetchall()

        conn.close()

        return featureAccess


def fetch_user_playlist_info(variant, userID, videoID, playlistID):
    """Fetches the playlist info of a playlist made by the user"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "add":
        # Check if playlist exists and if it was made by the user
        cursor.execute("SELECT * FROM playlists WHERE playlistID = ? AND userID = ?", (playlistID, userID))
        playlistExists = cursor.fetchone()

        if playlistExists:
            print(f"Playlist {playlistID} Found!")
            # Check if video is already in playlist
            cursor.execute("SELECT * FROM playlist_contents WHERE playlistID = ? AND videoID = ?",
                           (playlistID, videoID))
            videoInPlaylist = cursor.fetchone()

            if videoInPlaylist:
                # If the video is already in the playlist then remove it from the playlist
                cursor.execute("DELETE FROM playlist_contents WHERE playlistID = ? AND videoID = ?",
                               (playlistID, videoID))
                conn.commit()
                print("Video removed from playlist")
                conn.close()
            else:
                # If the video is not in the playlist then add it to the playlist
                cursor.execute("INSERT INTO playlist_contents (playlistID, videoID) VALUES (?, ?)",
                               (playlistID, videoID))
                conn.commit()
                print("Video added to playlist")
                conn.close()

        else:
            print("Playlist Not Found!")


def add_to_user_saved_videos(userID, videoID):
    """Adds the video the user requested to save to the saved videos playlist"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM playlists WHERE userID = ? and playlistType = ?", (userID, "watch_queue"))
    userSavedVideos = cursor.fetchone()

    fetch_user_playlist_info("add", userID, videoID, userSavedVideos[0])


def fetch_watch_page_details(variant, userID, videoID):
    """Fetches the necessary details from the database for the watch page for the selected video"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if variant == "saves":
        cursor.execute("SELECT * FROM playlists WHERE userID = ? and playlistType = ?", (userID, "watch_queue"))
        userSavedVideos = cursor.fetchone()  # Retrieve the playlist where saved videos are stored

        cursor.execute("SELECT * FROM playlist_contents WHERE playlistID = ? AND videoID = ?",
                       (userSavedVideos[0], videoID))
        isVideoSaved = cursor.fetchone()

        if isVideoSaved:
            return True
        else:
            return False


def fetch_user_watch_history(userID):
    """Fetches the user watch history from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    # Fetch the latest videos for the watch history section
    cursor.execute("""
                        SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                        videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                        profileColorSets.profilePictureBorderColor, videos.videoTags, accounts.accountStanding
                        FROM videos
                        JOIN accounts ON videos.userID = accounts.userID
                        JOIN profiles ON profiles.userID = accounts.userID
                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                        JOIN watchHistory ON watchHistory.videoID = videos.videoID
                        WHERE watchHistory.userID = ? AND accounts.accountStanding != 'Suspended'
                        ORDER BY watchHistory.historyDateTime DESC  -- Shows newest first
                        """, (userID,))
    watchHistory = cursor.fetchall()

    return watchHistory


def extract_tags_from_video(tags):
    tags = [tag.strip() for tag in tags.split(",")]

    return tags


def fetch_user_recommended_feed(userID):
    """Fetches the user recommended feed for the home page"""
    conn = connect_to_database()
    cursor = conn.cursor()
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

        cursor.execute(f"""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, 
                            videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor, 
                            profiles.channelURLEnabled, profiles.channelURL, accounts.accountStanding
                            FROM videos 
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE ({" OR ".join(["(',' || REPLACE(videoTags, ' ', '') || ',') LIKE ?"] * len(top_video_tags))}) AND accountStanding != 'Suspended'
                    """, [f"%,{tag.replace(' ', '')},%" for tag in top_video_tags])
        recommended_videos = cursor.fetchall()
    else:
        recommended_videos = []

    return recommended_videos


def fetch_video_for_watch_page(videoID):
    """Fetches the queried video information from the database"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("""SELECT * 
                                    FROM videos 
                                    JOIN profiles ON profiles.userID = videos.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE videoID = ?""", (videoID,))
    video = cursor.fetchone()

    cursor.execute("""
                    SELECT accountStanding
                    FROM videos
                    JOIN accounts ON accounts.userID = videos.userID
                    WHERE videoID = ?
                    """, (videoID,))
    accountStanding_check = cursor.fetchone()[0]

    return video, accountStanding_check


def fetch_comments_section(userID, videoID):
    """Fetches the comment section for the video"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("""
                            SELECT comments.commentID, accounts.username, comments.comment, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, comments.userID,
                            COUNT(likedComments.commentID) AS likeCount, SUM(likedComments.userID = ?) AS isLikedByUser, 
                            accounts.accountStanding
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            LEFT JOIN likedComments ON likedComments.commentID = comments.commentID
                            WHERE comments.videoID = ? AND accountStanding != 'Suspended'
                            GROUP BY comments.commentID
                            ORDER BY comments.commentID DESC 
                            """, (userID, videoID))
    comments = cursor.fetchall()

    return comments


def fetch_video_recommendation_board():
    """Fetches the video recommendation board for the login and register page"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM videos")

    num_of_videos = cursor.fetchone()[0]

    if num_of_videos:
        video_recommendation_1_randomizer = random.randint(1, num_of_videos)
        video_recommendation_2_randomizer = random.randint(1, num_of_videos)
        video_recommendation_3_randomizer = random.randint(1, num_of_videos)

        cursor.execute("SELECT * FROM videos WHERE videoID = ?", (video_recommendation_1_randomizer,))
        video_recommendation_1 = cursor.fetchone()

        cursor.execute("SELECT * FROM videos WHERE videoID = ?", (video_recommendation_2_randomizer,))
        video_recommendation_2 = cursor.fetchone()

        cursor.execute("SELECT * FROM videos WHERE videoID = ?", (video_recommendation_3_randomizer,))
        video_recommendation_3 = cursor.fetchone()

        return video_recommendation_1, video_recommendation_2, video_recommendation_3

    print(f"Total videos: {num_of_videos}")


def fetch_search_results(searchType, searchQueryForDB, userID):
    """Fetches videos that match or are related to the search query from the user"""
    conn = connect_to_database()
    cursor = conn.cursor()

    if searchType == "Regular":
        # Fetch the videos with the most views for the search results
        cursor.execute("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                            videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, accounts.accountStanding
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE videos.videoTitle LIKE ? AND accountStanding != 'Suspended'
                            ORDER BY views DESC  -- Shows newest first
                        """, (searchQueryForDB,))
        resultsFromSearch = cursor.fetchall()
        conn.close()
        return resultsFromSearch
    if searchType == "Subscriptions":
        # Fetch the videos with the most views for the search results
        cursor.execute("""
                                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                    profileColorSets.profilePictureBorderColor, accounts.accountStanding
                                    FROM videos
                                    JOIN accounts ON videos.userID = accounts.userID
                                    JOIN profiles ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE videos.videoTitle LIKE ? AND subscriptions.userID = ? AND accountStanding != 'Suspended'
                                    ORDER BY views DESC  -- Shows newest first
                                """, (searchQueryForDB, userID))
        resultsFromSearch = cursor.fetchall()
        conn.close()
        return resultsFromSearch


def fetch_account_standing(userID):
    """Fetches the account standing for a given userID"""
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("SELECT accountStanding FROM accounts WHERE userID = ?", (userID,))
    accountStanding = cursor.fetchone()[0]

    return accountStanding

