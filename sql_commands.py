import config

import random

from sqlalchemy import create_engine, text

from sqlalchemy.exc import IntegrityError

from collections import Counter

from datetime import datetime

# Set the location for the database
DB_engine = create_engine(config.sqlalchemy_db_path)


def connect_to_database():
    return DB_engine.connect()


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
                                WHERE notificationRecipientID = :notificationRecipientID
                                ORDER BY notificationDateTime DESC
                                         """),
                              {"notificationRecipientID": userID})
        notifications = result.fetchall()

        result = conn.execute(text(
            """SELECT COUNT(*) FROM notifications WHERE notificationRecipientID = :notificationRecipientID"""
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

        tag_parameters = {
            f"tag{i}": f"%,{tag.replace(' ', '')},%"
            for i, tag in enumerate(top_video_tags)
        }

        result = conn.execute(text(f"""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, 
                            videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor, 
                            profiles.channelURLEnabled, profiles.channelURL, accounts.accountStanding
                            FROM videos 
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE ({" OR ".join([f"(',' || REPLACE(videoTags, ' ', '') || ',') LIKE :tag{i}" for i in range(len(top_video_tags))])}) AND accountStanding != 'Suspended'
                    """), tag_parameters)
        recommended_videos = result.fetchall()
    else:
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
    accountStanding_check = result.fetchone()[0]

    return video, accountStanding_check


def fetch_comments_section(userID, videoID):
    """Fetches the comment section for the video"""
    conn = connect_to_database()

    result = conn.execute(text("""
                            SELECT comments.commentID, accounts.username, comments.comment, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, comments.userID,
                            COUNT(likedComments.commentID) AS likeCount, SUM(likedComments.userID = :userID) AS isLikedByUser, 
                            accounts.accountStanding
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            LEFT JOIN likedComments ON likedComments.commentID = comments.commentID
                            WHERE comments.videoID = :videoID AND accountStanding != 'Suspended'
                            GROUP BY comments.commentID
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
                            WHERE videos.videoTitle LIKE :videoTitle AND accountStanding != 'Suspended'
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
                                    WHERE videos.videoTitle LIKE :videoTitle AND subscriptions.userID = :userID AND accountStanding != 'Suspended'
                                    ORDER BY views DESC  -- Shows newest first
                                """), {"videoTitle": searchQueryForDB, "userID": userID})
        resultsFromSearch = result.fetchall()
        conn.close()
        return resultsFromSearch


def fetch_account_standing(userID):
    """Fetches the account standing for a given userID"""
    conn = connect_to_database()

    result = conn.execute(text("SELECT accountStanding FROM accounts WHERE userID = :userID"), {"userID": userID})
    accountStanding = result.fetchone()[0]

    return accountStanding


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

        return event_data, seasonState[0]
    else:
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
