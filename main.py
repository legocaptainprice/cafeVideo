from flask import Flask, render_template, request, url_for, session, jsonify, redirect, flash, abort
import sqlite3, createAccount, post, os, modifyAccount, sql_commands, config, manifest
from time_converter import time_ago, getVideoDatetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from numberSimplifier import viewSimplify

cafe = Flask(__name__)

cafe.config['UPLOAD_FOLDER'] = 'static/videos/'
cafe.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}
cafe.config['UPLOAD_THUMBNAILS_FOLDER'] = 'static/thumbnails'
cafe.config['ALLOWED_THUMBNAIL_EXTENSIONS'] = {'jpg', 'png', 'webp'}
cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'] = 'static/profile/pfp'
cafe.config['ALLOWED_PROFILE_PICTURE_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif', 'jpeg'}
cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'] = 'static/profile/banner'
cafe.config['ALLOWED_PROFILE_BANNER_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif'}

# Ensure the directories for these folders exist
os.makedirs(cafe.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'], exist_ok=True)

# Set the location for the database
cafeDatabasePath = config.sqlite_db_path

# Security related features
cafe.config.update(
    SESSION_COOKIE_HTTPONLY=config.session_cookie_httponly,
    SESSION_COOKIE_SECURE=config.session_cookie_secure,  # Enable if hosting publicly
    SESSION_COOKIE_SAMESITE=config.session_cookie_samesite
)
cafeSecretKey = os.getenv("SECRET_CAFE_KEY")  # You MUST set a secret key in your environment variables

if not cafeSecretKey:
    raise RuntimeError("SECRET_CAFE_KEY environment variable not set! This is required to run the server.")

cafe.config["SECRET_KEY"] = cafeSecretKey


# Algorithm should revolve around DB entries as well, for example a table with a bunch of tags from videos and the
# userID of the user that's watching the video, if they keep watching videos with a video game tag then more entries
# on the table with that userID and that tag will be entered then the server will curate their recommended feed
# based of the most popular tags that show up for that user.

# This codebase is a mess and needs to be revamped.


def allowedFiletypes(filename, allowedExtensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowedExtensions


def connect_to_database():
    # This is planned to be removed in favour of the same function in sql_commands.py
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn


@cafe.route('/')
def indexPage():
    """The home page for cafeVideo"""
    conn = connect_to_database()
    username = session.get("username")
    userID = session.get("userID")

    videos = sql_commands.fetch_latest_videos()

    if username:
        profilePicture = sql_commands.fetch_profile_info("minimal", userID)
        featureAccess = sql_commands.fetch_account_info("feature_access", userID)
        try:
            print(featureAccess[0][0])
        except:
            pass
        subscriptionsInfo = sql_commands.fetch_subscription_info(userID)
        # Fetch the latest videos for the subscriptions feed
        subscription_videos = sql_commands.fetch_subscription_videos("latest", userID)

        notifications = sql_commands.fetch_user_notifications("minimal", userID)
        conn.close()
        return render_template('index.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               subscription_videos=subscription_videos, featureAccess=featureAccess,
                               notifications=notifications)
    else:
        profilePicture = ["profilepicturetest.png"]
        conn.close()
        return redirect(url_for('explorePage'))


@cafe.route('/login')
def loginPage():
    """Displays the login page to the user by rendering the login page template"""
    username = session.get("username")

    if username:
        return redirect(url_for("indexPage"))
    else:
        return render_template('login.html')


@cafe.route('/loginAuth', methods=['GET', 'POST'])
def loginAuthAPI():
    """Handles the login authentication by checking the username and password to see if it matches a record on the
    database"""
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch user from accounts table
        cursor.execute('SELECT * FROM accounts WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        # Check if user and password is correct
        if user and check_password_hash(user["password"], password):
            session['userID'] = user['userID']  # Store userID in session
            session['username'] = user['username']  # Store username in session
            return redirect(url_for("indexPage"))

        return render_template("login.html", error="Invalid username or password")

    return cafe.redirect('/login.html', error=None)


@cafe.route('/registerAccount', methods=['POST'])
def registerAccountAPI():
    """Handles the registration process of the account by creating a new user record on the database"""
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    # Call the createAccount function and create the account with the username and hashed password
    success, message = createAccount.createAccount(username, hashed_password)

    if success:
        session['username'] = username
        return redirect(url_for("logout"))
    else:
        return render_template("login.html", error=message)


@cafe.route('/logout')
def logout():
    """Logs the user out of the account and redirects them back to the home page"""
    session.pop("userID", None)
    session.pop("username", None)
    return redirect(url_for("indexPage"))


@cafe.route('/upload')
def upload():
    """Webpage for uploading videos"""
    username = session.get('username')
    userID = session.get('userID')

    # If the user is not logged in, send them to the login page
    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        profilePicture = sql_commands.fetch_profile_info("minimal", userID)
        cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                        accounts.userID, accounts.username, channelURLEnabled, channelURL
                                        FROM profiles
                                        JOIN accounts ON profiles.userID = accounts.userID
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                        WHERE subscriptions.userID = ?""", (userID,))
        subscriptionsInfo = cursor.fetchall()
        notifications = sql_commands.fetch_user_notifications("minimal", userID)

        return render_template("upload.html", username=username, userID=session.get("userID"),
                               profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/uploadVideo', methods=['POST'])
def uploadVideo():
    """Function to retrieve video details"""
    if request.method == 'POST':
        if 'video' not in request.files:
            return 'No file part', 400
        videoFile = request.files['video']
        thumbnail = request.files['thumbnail']
        defaultThumbnail = 'videotemplate.png'

        if videoFile.filename == '':
            return 'No selected file', 400

        if thumbnail.filename == '':
            thumbnail.filename = defaultThumbnail

        if 'thumbnail' not in request.files:
            thumbnail.filename = defaultThumbnail

        if videoFile and allowedFiletypes(videoFile.filename, cafe.config['ALLOWED_EXTENSIONS']):
            # Upload the video file to its destination
            filename = secure_filename(videoFile.filename)
            filepath = os.path.join(cafe.config['UPLOAD_FOLDER'], filename)
            videoFile.save(filepath)
            # Upload the thumbnail file to its destination
            if thumbnail != defaultThumbnail:
                thumbnailFilename = secure_filename(thumbnail.filename)
                thumbnailPath = os.path.join(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], thumbnailFilename)
                thumbnail.save(thumbnailPath)
            else:
                thumbnailFilename = secure_filename(thumbnail.filename)
            userID = session.get('userID')
            title = request.form['title']
            description = request.form['description']
            videoTags = request.form['videoTags']
            # videoFile = request.form['videoURL']

            success, message = post.uploadVideoToDatabase(userID, title, description, videoTags, filename,
                                                          thumbnailFilename)

            if success:
                return redirect(url_for('indexPage'))
            else:
                return render_template('upload.html', error=message)


@cafe.route('/watch')
def watchPage():
    """Function to display the watch page"""
    #  userAgent = request.user_agent.string
    videoID = request.args.get('v')
    session['redirectToVideoID'] = videoID
    username = session.get('username')
    userID = session.get('userID')
    #  print(userAgent)

    #  if "AppleWebKit" in str(userAgent):
    #      print("you are using Safari")

    if videoID:
        # Retrieve video details
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""SELECT * 
                                FROM videos 
                                JOIN profiles ON profiles.userID = videos.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE videoID = ?""", (videoID,))
        video = cursor.fetchone()

        print(video)

        if video:
            # If there is a video go to the video
            # Fetch the latest videos for the new videos feed
            cursor.execute("SELECT views FROM videos WHERE videoID = ?", (videoID,))
            viewCount = cursor.fetchone()
            viewCount = viewCount[0]
            if viewCount:
                viewCount = viewCount + 1
                currentViewCount = viewSimplify(viewCount)
                cursor.execute("UPDATE videos SET views = ? WHERE videoID = ?", (viewCount, videoID))
            else:
                addFirstView = 1
                cursor.execute("UPDATE videos SET views = ? WHERE videoID = ?", (addFirstView, videoID))
                currentViewCount = addFirstView
            conn.commit()
            cursor.execute("SELECT username FROM accounts WHERE userID = ?", (video[1],))
            creatorUsername = cursor.fetchone()
            cursor.execute("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            ORDER BY videoID DESC  -- Shows newest first
                        """)
            videos = cursor.fetchall()  # List of tuples
            cursor.execute("""
                            SELECT comments.commentID, accounts.username, comments.comment, profiles.profilePicture, 
                            profileColorSets.profilePictureBorderColor, comments.userID, 
                            COUNT(likedComments.commentID) AS likeCount, SUM(likedComments.userID = ?) AS isLikedByUser
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            LEFT JOIN likedComments ON likedComments.commentID = comments.commentID
                            WHERE comments.videoID = ? 
                            GROUP BY comments.commentID
                            ORDER BY comments.commentID DESC 
                        """, (session.get("userID"), videoID))
            comments = cursor.fetchall()
            print(comments)

            num_of_comments = len(comments)
            cursor.execute("SELECT * FROM subscriptions WHERE subscribedToUserID = ?", (video[1],))
            subscribers = cursor.fetchall()
            num_of_subscribers = len(subscribers)
            cursor.execute("SELECT * FROM subscriptions WHERE userID = ? AND subscribedToUserID = ?",
                           (session.get("userID"), video[1]))
            isSubscribedToChannel = cursor.fetchone()
            if isSubscribedToChannel:
                isSubscribedToChannel = isSubscribedToChannel[0]
            cursor.execute("SELECT * FROM likedVideos WHERE videoID = ?", (videoID,))
            likes = cursor.fetchall()
            num_of_likes = len(likes)
            cursor.execute("SELECT * FROM likedVideos WHERE videoID = ? AND userID = ?",
                           (videoID, session.get("userID")))
            isLikedVideo = cursor.fetchone()
            if isLikedVideo:
                isLikedVideo = isLikedVideo[0]
            timestamp = int(video[6])
            datePublished = getVideoDatetime(timestamp)

            if username:
                post.sendWatchedVideoToDatabase(userID, videoID)  # Add video to user's watch history

                cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                        channelURLEnabled, channelURL
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID,))
                profilePicture = cursor.fetchone()
                notifications = sql_commands.fetch_user_notifications("minimal", userID)
                print(notifications)

                # Retrieve playlists by the user
                # Fetch the playlists created by the user
                cursor.execute("""
                                        SELECT playlists.playlistID, playlists.userID, playlists.playlistName, playlists.playlistType, 
                                        playlists.visibilityType, accounts.username, profiles.profilePicture, 
                                        profileColorSets.profilePictureBorderColor, COUNT(playlist_contents.videoID) AS videoCount
                                        FROM playlists
                                        JOIN accounts ON playlists.userID = accounts.userID
                                        JOIN profiles ON profiles.userID = accounts.userID
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        LEFT JOIN playlist_contents ON playlists.playlistID = playlist_contents.playlistID
                                        WHERE playlists.userID = ?
                                        GROUP BY playlists.playlistID
                                        ORDER BY playlists.playlistID DESC
                                    """, (userID,))
                userPlaylists = cursor.fetchall()  # List of tuples

                isVideoSaved = sql_commands.fetch_watch_page_details("saves", userID, videoID)

            else:
                profilePicture = ["profilepicturetest.png"]
                notifications = []
                userPlaylists = []
                isVideoSaved = False

            return render_template('watch.html', video=video, username=username, videos=videos,
                                   creatorUsername=creatorUsername, comments=comments, userID=userID,
                                   creatorUserID=video[1], num_of_comments=num_of_comments,
                                   currentViewCount=currentViewCount, num_of_subscribers=num_of_subscribers,
                                   isSubscribedToChannel=isSubscribedToChannel, num_of_likes=num_of_likes,
                                   isLikedVideo=isLikedVideo, datePublished=datePublished, time_ago=time_ago,
                                   profilePicture=profilePicture, notifications=notifications,
                                   viewSimplifier=viewSimplify, userPlaylists=userPlaylists, isVideoSaved=isVideoSaved)
        else:
            return "Video not found", 404
    else:
        return "VideoID is required", 400


@cafe.route('/postComment', methods=["POST"])
def sendComment():
    if request.method == "POST":
        if "userID" in session:
            userID = session.get("userID")
            videoID = session.get("redirectToVideoID")

            comment = request.form["postComment"]

            post.sendCommentToDatabase(videoID, userID, comment)

            return redirect(f'/watch?v={videoID}')
        else:
            return redirect(url_for('loginPage'))


@cafe.route('/postReply', methods=["POST"])
def sendReply():
    if request.method == "POST":
        userID = session.get("userID")
        videoID = session.get("redirectToVideoID")
        commentID = session.get("replyToCommentID")

        reply = request.form["postReply"]

        post.sendReplyToDatabase(commentID, userID, reply)

        return redirect(f'/watch?v={videoID}')


@cafe.route('/searchRequest', methods=["POST"])
def searchRequest():
    searchQueryRequest = request.form["search"]
    return redirect(f'/results?search_query={searchQueryRequest}')


@cafe.route('/results')
def searchForVideo():
    searchQuery = request.args.get("search_query")
    searchQueryForDB = f"%{searchQuery}%"
    username = session.get("username")
    userID = session.get("userID")

    if searchQuery:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch the videos with the most views for the search results
        cursor.execute("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    WHERE videos.videoTitle LIKE ?
                    ORDER BY views DESC  -- Shows newest first
                """, (searchQueryForDB,))
        videos = cursor.fetchall()  # List of tuples

        print(videos)

        num_of_videos = len(videos)

        if username:
            cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                    channelURLEnabled, channelURL
                                    FROM profiles 
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE userID = ?""", (userID,))
            profilePicture = cursor.fetchone()
            cursor.execute("""
                                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                                    accounts.userID, accounts.username, channelURLEnabled, channelURL
                                                    FROM profiles
                                                    JOIN accounts ON profiles.userID = accounts.userID
                                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                                    WHERE subscriptions.userID = ?""", (userID,))
            subscriptionsInfo = cursor.fetchall()
            notifications = sql_commands.fetch_user_notifications("minimal", userID)
            conn.close()
            return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos,
                                   num_of_videos=num_of_videos, userID=userID, time_ago=time_ago,
                                   profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                                   notifications=notifications)
        else:
            profilePicture = ["profilepicturetest.png"]
            notifications = []
            conn.close()
            return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos,
                                   num_of_videos=num_of_videos, userID=userID, time_ago=time_ago,
                                   profilePicture=profilePicture, notifications=notifications)

    else:
        return redirect(url_for("indexPage"))


@cafe.route('/channel')
def getAccountProfile():
    userID = request.args.get('id')
    username = session.get("username")
    userID_session = session.get("userID")

    if userID:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Check if the userID exists
        cursor.execute("SELECT * FROM accounts WHERE userID = ?", (userID,))
        foundUserID = cursor.fetchone()

        if foundUserID:
            cursor.execute("""
                                SELECT * 
                                FROM accounts 
                                JOIN profiles ON accounts.userID = profiles.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE accounts.userID = ?
                                """, (userID,))
            profileDetails = cursor.fetchone()

            # Fetch the latest videos for the new videos feed
            cursor.execute("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                WHERE videos.userID = ?
                                ORDER BY videoID DESC  -- Shows newest first
                            """, (userID,))
            videos = cursor.fetchall()  # List of tuples
            num_of_videos = len(videos)

            cursor.execute("""
                            SELECT * 
                            FROM subscriptions
                            WHERE subscribedToUserID = ?
                            """, (userID,))
            subscribers = cursor.fetchall()
            num_of_subscribers = len(subscribers)

            if username:
                cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                        channelURLEnabled, channelURL
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID_session,))
                profilePicture = cursor.fetchone()
                cursor.execute("""
                                                                    SELECT profilePicture, 
                                                                    profileColorSets.profilePictureBorderColor, 
                                                                    accounts.userID, accounts.username, 
                                                                    channelURLEnabled, channelURL
                                                                    FROM profiles
                                                                    JOIN accounts ON profiles.userID = accounts.userID
                                                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                                                    WHERE subscriptions.userID = ?""",
                               (userID_session,))
                subscriptionsInfo = cursor.fetchall()

                cursor.execute("SELECT * FROM subscriptions WHERE userID = ? AND subscribedToUserID = ?",
                               (userID_session, userID))
                isSubscribedToChannel = cursor.fetchone()
                if isSubscribedToChannel:
                    isSubscribedToChannel = isSubscribedToChannel[0]
                notifications = sql_commands.fetch_user_notifications("minimal", userID_session)
                return render_template("profile.html", username=username, profileDetails=profileDetails, videos=videos,
                                       userID=userID_session, time_ago=time_ago, profilePicture=profilePicture,
                                       num_of_subscribers=num_of_subscribers, subscriptionsInfo=subscriptionsInfo,
                                       channelID=userID, isSubscribedToChannel=isSubscribedToChannel,
                                       num_of_videos=num_of_videos, notifications=notifications)

            else:
                profilePicture = ["profilepicturetest.png"]
                notifications = []
                return render_template("profile.html", username=username, profileDetails=profileDetails, videos=videos,
                                       userID=userID_session, time_ago=time_ago, profilePicture=profilePicture,
                                       num_of_subscribers=num_of_subscribers, channelID=userID,
                                       num_of_videos=num_of_videos, notifications=notifications)
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(url_for("indexPage"))


@cafe.route('/<channelURL>')
def redirectPage(channelURL):
    """The profile of the user by their channel URL"""
    viewerUserID = session.get('userID')
    viewerUsername = session.get("username")
    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("SELECT channelURLEnabled FROM profiles WHERE channelURL = ?", (channelURL,))
    channelURLEnabled = cursor.fetchone()

    try:
        if channelURLEnabled[0] == 1:
            cursor.execute("SELECT userID FROM profiles WHERE channelURL = ?", (channelURL,))
            userID = cursor.fetchone()
            userID = userID[0]
            print(userID)
            with cafe.test_request_context(f'channel?id={userID}'):
                session["username"] = viewerUsername
                session["userID"] = viewerUserID
                return getAccountProfile()
        else:
            return abort(404)
    except:
        return abort(404)


@cafe.route('/subscribeUser', methods=["POST"])
def subscribeToUser():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    creatorUserID = request.args.get('creatorID')
    subscriberUserID = session["userID"]

    if creatorUserID is None:
        return redirect(url_for('indexPage'))

    if int(creatorUserID) != int(subscriberUserID):
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM subscriptions WHERE userID = ? AND subscribedToUserID = ?",
                       (subscriberUserID, creatorUserID))
        isSubscribed = cursor.fetchone()

        if isSubscribed:
            cursor.execute("DELETE FROM subscriptions WHERE userID = ? AND subscribedToUserID = ?",
                           (subscriberUserID, creatorUserID))
            conn.commit()
            print("User has been unsubscribed")
            conn.close()
            return redirect(request.referrer)
        else:
            cursor.execute("INSERT INTO subscriptions (userID, subscribedToUserID) VALUES (?, ?)",
                           (subscriberUserID, creatorUserID))
            conn.commit()

            # Send the notification to the database

            cursor.execute("SELECT username FROM accounts WHERE userID = ?", (subscriberUserID,))
            usernameOfSubscriber = cursor.fetchone()
            print(usernameOfSubscriber[0])

            post.sendNotificationToDatabase(creatorUserID, subscriberUserID,
                                            f"{usernameOfSubscriber[0]} has subscribed to your channel", "",
                                            "subscribedToChannel", "None")

            conn.close()
            return redirect(request.referrer)
    else:
        return redirect(request.referrer)


@cafe.route('/likeVideo', methods=["POST"])
def likeVideoFromCreatorID():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    videoID = request.args.get('videoID')
    creatorUserID = request.args.get('creatorID')
    userID = session["userID"]

    if int(creatorUserID) != int(userID):
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM videos WHERE videoID = ?", (videoID,))
        videoExists = cursor.fetchone()
        if videoExists:

            cursor.execute("SELECT * FROM likedVideos WHERE videoID = ? AND creatorID = ? AND userID = ?",
                           (videoID, creatorUserID, userID))
            isLikedVideo = cursor.fetchone()

            if isLikedVideo:
                cursor.execute("DELETE FROM likedVideos WHERE videoID = ? AND creatorID = ? AND userID = ?",
                               (videoID, creatorUserID, userID))
                conn.commit()
                print("User has unliked the video")
                conn.close()
                return redirect(request.referrer)
            else:
                cursor.execute("INSERT INTO likedVideos (videoID, creatorID, userID) VALUES (?, ?, ?)",
                               (videoID, creatorUserID, userID))
                conn.commit()
                cursor.execute("SELECT username FROM accounts WHERE userID = ?", (userID,))
                usernameOfLiker = cursor.fetchone()
                print(usernameOfLiker[0])
                cursor.execute("SELECT videoTitle FROM videos WHERE videoID = ?", (videoID,))
                videoTitle = cursor.fetchone()
                print(videoTitle[0])
                conn.close()

                post.sendNotificationToDatabase(creatorUserID, userID, f"{usernameOfLiker[0]} liked your video",
                                                f"you received a like on {videoTitle[0]}", "likedVideo", "None")

                return redirect(request.referrer)
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(request.referrer)


@cafe.route('/likeComment', methods=["POST"])
def likeCommentFromCommenterID():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    commentID = request.args.get('commentID')
    commenterID = request.args.get('commenterID')
    userID = session['userID']

    if int(commenterID) != int(userID):
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM comments WHERE commentID = ?", (commentID,))
        commentExists = cursor.fetchone()
        if commentExists:

            cursor.execute("SELECT * FROM likedComments WHERE commentID = ? AND commenterID = ? AND userID = ?",
                           (commentID, commenterID, userID))
            isLikedComment = cursor.fetchone()

            if isLikedComment:
                cursor.execute("DELETE FROM likedComments WHERE commentID = ? AND commenterID = ? AND userID = ?",
                               (commentID, commenterID, userID))
                conn.commit()
                print("User has unliked the comment")
                conn.close()
                return redirect(request.referrer)
            else:
                cursor.execute("INSERT INTO likedComments (commentID, commenterID, userID) VALUES (?, ?, ?)",
                               (commentID, commenterID, userID))
                conn.commit()
                print("User has liked the comment")

                # Send the notification to the database

                cursor.execute("SELECT username FROM accounts WHERE userID = ?", (userID,))
                usernameOfLiker = cursor.fetchone()
                print(usernameOfLiker[0])

                # Cutting corners here for a sec

                post.sendNotificationToDatabase(commenterID, userID, f"{usernameOfLiker[0]} has liked your comment",
                                                "", "likedComment", "None")
                conn.close()
                return redirect(request.referrer)
        else:
            return redirect(url_for('indexPage'))
    else:
        return redirect(request.referrer)


@cafe.route('/likeReply')
def likeReplyFromReplierID():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    replyID = session.get("replyID")
    replierID = session.get("replierID")
    userID = session["userID"]

    if int(replierID) != int(userID):
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM replies WHERE replyID = ?", (replyID,))
        replyExists = cursor.fetchone()

        if replyExists:
            cursor.execute("SELECT * FROM likedReplies WHERE replyID = ? AND replierID = ? AND userID = ?",
                           (replyID, replierID, userID))
            isLikedReply = cursor.fetchone()

            if isLikedReply:
                cursor.execute("DELETE FROM likedReplies WHERE replyID = ? AND replierID = ? AND userID = ?",
                               (replyID, replierID, userID))
                conn.commit()
                print("User has unliked the reply")
                conn.close()
                return redirect(request.referrer)
            else:
                cursor.execute("INSERT INTO likedReplies (replyID, replierID, userID) VALUES (?, ?, ?)",
                               (replyID, replierID, userID))
                conn.commit()
                print("User has liked the reply")
                conn.close()
                return redirect(request.referrer)
        else:
            return redirect(url_for('indexPage'))
    else:
        return redirect(request.referrer)


@cafe.route('/editProfile')
def editUserProfile():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileBanner, profileColorSets.profilePictureBorderColor, 
                                channelURLEnabled, channelURL 
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profileInfo = cursor.fetchone()

        # Need to also add a way to have some hidden themes only available for certain events
        # This can be done by adding a hidden column to the profileColorSets table
        cursor.execute('SELECT profileSetID, profileSetName FROM profileColorSets')
        profileColorSets = cursor.fetchall()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                accounts.username, channelURLEnabled, channelURL
                                FROM profiles
                                JOIN accounts ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

        # Fetch the amount of features the user has access to
        cursor.execute("""
                        SELECT * 
                        FROM feature_access
                        WHERE userID = ?
                        """, (userID,))
        userAccessList = cursor.fetchall()

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

        if userAccessList:
            userAccessDisplay = []
            for userAccess in userAccessList:
                cursor.execute("""
                                    SELECT *
                                    FROM feature_gating
                                    WHERE featureID = ?
                                    """, (userAccess[0],))
                feature = cursor.fetchone()
                userAccessDisplay.append(feature)
        else:
            userAccessDisplay = False

        return render_template("edit_profile.html", username=username, userID=userID, profileInfo=profileInfo,
                               profileColorSets=profileColorSets, subscriptionsInfo=subscriptionsInfo,
                               userAccessDisplay=userAccessDisplay, notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/accountSettings')
def getAccountSettings():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileBanner, channelURL, 
                                profileColorSets.profilePictureBorderColor, channelURLEnabled
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profileInfo = cursor.fetchone()

        cursor.execute('SELECT profileSetID, profileSetName FROM profileColorSets')
        profileColorSets = cursor.fetchall()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                accounts.username, channelURLEnabled, channelURL
                                FROM profiles
                                JOIN accounts ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

        # Fetch the amount of features the user has access to
        cursor.execute("""
                            SELECT * 
                            FROM feature_access
                            WHERE userID = ?
                            """, (userID,))
        userAccessList = cursor.fetchall()

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

        if userAccessList:
            userAccessDisplay = []
            for userAccess in userAccessList:
                cursor.execute("""
                                        SELECT *
                                        FROM feature_gating
                                        WHERE featureID = ?
                                        """, (userAccess[0],))
                feature = cursor.fetchone()
                userAccessDisplay.append(feature)
        else:
            userAccessDisplay = False

        return render_template("account_settings.html", username=username, userID=userID, profileInfo=profileInfo,
                               profileColorSets=profileColorSets, subscriptionsInfo=subscriptionsInfo,
                               userAccessDisplay=userAccessDisplay, notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/confirmAccountEdit', methods=["POST"])
def confirmAccountDetailsEdit():
    if request.method == "POST":
        try:
            userID = session.get('userID')
        except:
            return redirect(url_for('indexPage'))
        username = request.form["usernameEdit"]
        channelURL = request.form["channelURL"]

        success, message = modifyAccount.changeAccountDetailsConfirm(userID, username, channelURL)

        if success:
            session['username'] = username  # Store username in session
            return redirect(url_for('getAccountSettings'))
        else:
            flash(message, 'error')
            return redirect(url_for('getAccountSettings'))


@cafe.route('/confirmProfileEdit', methods=["POST"])
def saveProfileSettings():
    if request.method == "POST":
        profileBanner = request.files["profileBanner"]
        profilePicture = request.files["profilePicture"]
        profileBannerDefault = "profilebannertemplate.png"
        profilePictureDefault = "profilepicturetest.png"
        userID = session.get('userID')
        bio = request.form["bio"]
        try:
            profileColorTheme = request.form["profileTheme"]
        except:
            profileColorTheme = 5
            print("Defaulting")
        success = False
        message = ""

        if profileBanner.filename == '':
            print("No profile banner filename")

        if profilePicture.filename == '':
            print("No profile picture filename")

        if 'profileBanner' not in request.files:
            print("No profile banner filename")

        if 'profilePicture' not in request.files:
            print("No profile picture filename")

        # cursor.execute("UPDATE videos SET views = ? WHERE videoID = ?", (viewCount, videoID))

        if profilePicture and allowedFiletypes(profilePicture.filename,
                                               cafe.config['ALLOWED_PROFILE_PICTURE_EXTENSIONS']):
            profilePictureFilename = secure_filename(profilePicture.filename)
            profilePicturePath = os.path.join(cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'], profilePictureFilename)
            profilePicture.save(profilePicturePath)

            successfulProfilePictureUpload, message = post.uploadProfilePictureToDatabase(profilePictureFilename,
                                                                                          userID)
            if successfulProfilePictureUpload:
                success = True

        if profileBanner and allowedFiletypes(profileBanner.filename, cafe.config['ALLOWED_PROFILE_BANNER_EXTENSIONS']):
            profileBannerFilename = secure_filename(profileBanner.filename)
            profileBannerPath = os.path.join(cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'], profileBannerFilename)
            profileBanner.save(profileBannerPath)

            successfulProfileBannerUpload, message = post.uploadProfileBannerToDatabase(profileBannerFilename, userID)
            if successfulProfileBannerUpload:
                success = True

        if bio != '':
            success, message = post.sendProfileBioToDatabase(bio, userID)

        if profileColorTheme != '':
            success, message = post.updateProfileColorTheme(profileColorTheme, userID)

        if success:
            return redirect(url_for('getAccountProfile'))
        else:
            flash(message, 'error')
            return redirect(url_for('editUserProfile'))


@cafe.errorhandler(404)
def pageNotFound(error):
    username = session.get('username')
    userID = session.get('userID')

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                channelURL
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

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

        return render_template('404.html', username=username, userID=userID,
                               profilePicture=profilePicture, notifications=notifications), 404
    else:
        return render_template('404.html'), 404


@cafe.errorhandler(405)
def pageForbidden(error):
    return pageNotFound(NotFound)


@cafe.route('/subscriptions')
def accountSubscriptions():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch the latest videos for the subscriptions feed
        cursor.execute("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                    WHERE subscriptions.userID = ?
                    ORDER BY videoID DESC  -- Shows newest first
                """, (userID,))
        videos = cursor.fetchall()  # List of tuples

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                channelURL
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                accounts.username, channelURLEnabled, channelURL
                                FROM profiles
                                JOIN accounts ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

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
        return render_template('subscriptions.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/explore')
def explorePage():
    conn = connect_to_database()
    cursor = conn.cursor()
    username = session.get("username")
    userID = session.get("userID")

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
    videos = cursor.fetchall()  # List of tuples

    if username:
        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, 
                                    channelURLEnabled, channelURL
                                    FROM profiles 
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()
        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                    accounts.username, channelURLEnabled, channelURL
                                    FROM profiles
                                    JOIN accounts ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE subscriptions.userID = ?""", (userID,))
        subscriptionsInfo = cursor.fetchall()
        print(subscriptionsInfo)
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
        return render_template('explore.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        profilePicture = ["profilepicturetest.png"]
        notifications = []
    conn.close()
    return render_template('explore.html', username=username, videos=videos, userID=userID,
                           time_ago=time_ago, profilePicture=profilePicture, notifications=notifications)


@cafe.route('/lattes')
def lattePage():
    username = session.get("username")
    userID = session.get("userID")
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
    lattes = cursor.fetchall()  # List of tuples

    cursor.execute("""
                            SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                            channelURL
                            FROM profiles 
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE userID = ?""", (userID,))
    profilePicture = cursor.fetchone()
    cursor.execute("""
                            SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                            accounts.username, channelURLEnabled, channelURL
                            FROM profiles
                            JOIN accounts ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                            WHERE subscriptions.userID = ?""", (userID,))
    subscriptionsInfo = cursor.fetchall()

    if username:

        # Check if user has access
        cursor.execute("""
                        SELECT userID 
                        FROM feature_access 
                        WHERE featureID = 1
                        """)
        usersList = cursor.fetchall()

        print(usersList)

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

        for user in usersList:
            if user[0] == userID:
                return render_template('lattes.html', username=username, videos=lattes, userID=userID,
                                       time_ago=time_ago, profilePicture=profilePicture,
                                       subscriptionsInfo=subscriptionsInfo, notifications=notifications)
            else:
                return abort(404)
    else:
        return abort(404)


@cafe.route("/likes/videos")
def likedVideosPage():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch the latest videos for the liked videos section
        cursor.execute("""
                        SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                        videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                        profileColorSets.profilePictureBorderColor
                        FROM videos
                        JOIN accounts ON videos.userID = accounts.userID
                        JOIN profiles ON profiles.userID = accounts.userID
                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                        JOIN likedVideos ON likedVideos.videoID = videos.videoID
                        WHERE likedVideos.userID = ?
                        ORDER BY videos.videoID DESC  -- Shows newest first
                    """, (userID,))
        videos = cursor.fetchall()  # List of tuples

        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                    channelURL
                                    FROM profiles 
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                    accounts.username, channelURLEnabled, channelURL
                                    FROM profiles
                                    JOIN accounts ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

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
        return render_template('liked_videos.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route("/history/videos")
def watchHistory():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch the latest videos for the watch history section
        cursor.execute("""
                        SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                        videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                        profileColorSets.profilePictureBorderColor
                        FROM videos
                        JOIN accounts ON videos.userID = accounts.userID
                        JOIN profiles ON profiles.userID = accounts.userID
                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                        JOIN watchHistory ON watchHistory.videoID = videos.videoID
                        WHERE watchHistory.userID = ?
                        ORDER BY watchHistory.historyDateTime DESC  -- Shows newest first
                    """, (userID,))
        videos = cursor.fetchall()  # List of tuples

        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                    channelURL
                                    FROM profiles 
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                    accounts.username, channelURLEnabled, channelURL
                                    FROM profiles
                                    JOIN accounts ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

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
        return render_template('history.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/playlists/videos')
def userPlaylist():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        # Fetch the playlists created by the user
        cursor.execute("""
                        SELECT playlists.playlistID, playlists.userID, playlists.playlistName, playlists.playlistType, 
                        playlists.visibilityType, accounts.username, profiles.profilePicture, 
                        profileColorSets.profilePictureBorderColor, COUNT(playlist_contents.videoID) AS videoCount
                        FROM playlists
                        JOIN accounts ON playlists.userID = accounts.userID
                        JOIN profiles ON profiles.userID = accounts.userID
                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                        LEFT JOIN playlist_contents ON playlists.playlistID = playlist_contents.playlistID
                        WHERE playlists.userID = ?
                        GROUP BY playlists.playlistID
                        ORDER BY playlists.playlistID DESC
                    """, (userID,))
        userPlaylists = cursor.fetchall()  # List of tuples

        print(userPlaylists)

        cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                        channelURL
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                        accounts.username, channelURLEnabled, channelURL
                                        FROM profiles
                                        JOIN accounts ON profiles.userID = accounts.userID
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                        WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

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
        return render_template('playlists.html', username=username, userPlaylists=userPlaylists, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/playlists/create', methods=["POST"])
def playlistCreate():
    if request.method == "POST":
        try:
            userID = session.get('userID')
        except:
            return redirect(url_for('indexPage'))

        playlistName = request.form["name"]
        playlistDescription = request.form["description"]
        playlistVisibility = request.form["visibility"]

        print(
            f"Playlist Name: {playlistName}\nPlaylist Description: {playlistDescription}\nPlaylistVisibility: {playlistVisibility}")

        conn = connect_to_database()
        cursor = conn.cursor()

        if playlistName:
            cursor.execute("INSERT INTO playlists (userID, playlistName, playlistDescription, playlistType, "
                           "visibilityType) VALUES (?, ?, ?, ?, ?)",
                           (userID, playlistName, playlistDescription, "Regular", playlistVisibility))
            conn.commit()

        return redirect(request.referrer)
    else:
        return abort(404)


@cafe.route("/playlist/<playlistID>/add", methods=["POST"])
def playlistAdd(playlistID):
    if request.method == "POST":
        try:
            userID = session.get('userID')
            videoID = request.args.get('v')

            sql_commands.fetch_user_playlist_info("add", userID, videoID, playlistID)

            return redirect(request.referrer)

        except:
            return redirect(url_for('indexPage'))

    else:
        return abort(404)


@cafe.route("/playlist/<playlistID>/videos")
def viewPlaylist(playlistID):
    username = session.get('username')
    userID = session.get('userID')

    conn = connect_to_database()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM playlists WHERE playlistID = ?", (playlistID,))
    playlistIDFound = cursor.fetchone()

    if playlistIDFound:
        print(f"Playlist ID: {playlistIDFound[0]} has been found!\nPlaylist Title: {playlistIDFound[2]}")

        print(playlistIDFound[2])

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                        channelURL
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                accounts.username, channelURLEnabled, channelURL
                                FROM profiles
                                JOIN accounts ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                WHERE subscriptions.userID = ?""",
                       (userID,))
        subscriptionsInfo = cursor.fetchall()

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

        # Fetch the latest videos for the playlist section
        cursor.execute("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                profileColorSets.profilePictureBorderColor
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                JOIN profiles ON profiles.userID = accounts.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                JOIN playlist_contents ON playlist_contents.videoID = videos.videoID
                                WHERE playlist_contents.playlistID = ?
                                ORDER BY playlist_contents.videoID DESC  -- Shows newest first
                            """, (playlistID,))
        videos = cursor.fetchall()  # List of tuples

        return render_template('playlist.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, profilePicture=profilePicture, subscriptionsInfo=subscriptionsInfo,
                               notifications=notifications, playlistInfo=playlistIDFound, watch_queue=False)
    else:
        abort(404)


@cafe.route('/saves')
def viewSaves():
    username = session.get('username')
    userID = session.get('userID')

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM playlists WHERE userID = ? AND playlistType = ?", (userID, "watch_queue"))
        playlistIDFound = cursor.fetchone()

        if playlistIDFound:
            print(f"Playlist ID: {playlistIDFound[0]} has been found!\nPlaylist Title: {playlistIDFound[2]}")

            print(playlistIDFound[2])

            cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                            channelURL
                                            FROM profiles 
                                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                            WHERE userID = ?""", (userID,))
            profilePicture = cursor.fetchone()

            cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor, accounts.userID, 
                                    accounts.username, channelURLEnabled, channelURL
                                    FROM profiles
                                    JOIN accounts ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN subscriptions ON subscriptions.subscribedToUserID = accounts.userID
                                    WHERE subscriptions.userID = ?""",
                           (userID,))
            subscriptionsInfo = cursor.fetchall()

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

            # Fetch the latest videos for the playlist section
            cursor.execute("""
                                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, 
                                    videos.videoThumbnail, videos.datetime, profiles.profilePicture, 
                                    profileColorSets.profilePictureBorderColor
                                    FROM videos
                                    JOIN accounts ON videos.userID = accounts.userID
                                    JOIN profiles ON profiles.userID = accounts.userID
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    JOIN playlist_contents ON playlist_contents.videoID = videos.videoID
                                    WHERE playlist_contents.playlistID = ?
                                    ORDER BY playlist_contents.videoID DESC  -- Shows newest first
                                """, (playlistIDFound[0],))
            videos = cursor.fetchall()  # List of tuples

            return render_template('playlist.html', username=username, videos=videos, userID=userID,
                                   time_ago=time_ago, profilePicture=profilePicture,
                                   subscriptionsInfo=subscriptionsInfo,
                                   notifications=notifications, playlistInfo=playlistIDFound, watch_queue=True)
        else:
            abort(404)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/about')
def aboutPage():
    username = session.get('username')
    userID = session.get('userID')

    WEB_TITLE = manifest.WEB_TITLE
    VERSION = f"{manifest.MAJOR}.{manifest.MINOR}.{manifest.PATCH}"
    CHANNEL = manifest.CHANNEL
    CODENAME = manifest.CODENAME

    if username:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor, channelURLEnabled, 
                                channelURL
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

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

        return render_template('about.html', username=username, userID=userID,
                               profilePicture=profilePicture, notifications=notifications, WEB_TITLE=WEB_TITLE,
                               VERSION=VERSION, CODENAME=CODENAME, CHANNEL=CHANNEL)
    else:
        return render_template('about.html', WEB_TITLE=WEB_TITLE,
                               VERSION=VERSION, CODENAME=CODENAME, CHANNEL=CHANNEL)


@cafe.route('/saves/add', methods=["POST"])
def saveVideo():
    if request.method == "POST":
        try:
            userID = session.get('userID')
            videoID = request.args.get('v')

            sql_commands.add_to_user_saved_videos(userID, videoID)

            return redirect(request.referrer)

        except:
            return redirect(url_for('indexPage'))


@cafe.route('/corners')
def corners_explore():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        profilePicture = sql_commands.fetch_profile_info("minimal", userID)
        featureAccess = sql_commands.fetch_account_info("feature_access", userID)
        try:
            print(featureAccess[0][0])
        except:
            pass
        subscriptionsInfo = sql_commands.fetch_subscription_info(userID)

        notifications = sql_commands.fetch_user_notifications("minimal", userID)
        return render_template('corners.html', username=username, userID=userID,  profilePicture=profilePicture,
                               subscriptionsInfo=subscriptionsInfo, featureAccess=featureAccess,
                               notifications=notifications)
    else:
        profilePicture = ["profilepicturetest.png"]
        return redirect(url_for('explorePage'))


cafe.run(config.ip_address, config.port, debug=config.debug)
