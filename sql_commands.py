import sqlite3

import config

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
                profiles.channelURLEnabled, profiles.channelURL
                FROM videos
                JOIN accounts ON videos.userID = accounts.userID
                JOIN profiles ON profiles.userID = accounts.userID
                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
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
                            accounts.username, channelURLEnabled, channelURL
                            FROM profiles
                            JOIN accounts ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = ?""", (userID,))
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
                                WHERE subscriptions.userID = ?
                                ORDER BY videoID DESC  -- Shows newest first
                                LIMIT 12
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
