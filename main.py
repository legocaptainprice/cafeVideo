from flask import Flask, render_template, request, url_for, session, jsonify, redirect, flash
import sqlite3, createAccount, post, os
from time_converter import time_ago
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

cafe = Flask(__name__)
cafe.secret_key = "supersecretkey"

cafe.config['UPLOAD_FOLDER'] = 'static/videos/'
cafe.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}
cafe.config['UPLOAD_THUMBNAILS_FOLDER'] = 'static/thumbnails'
cafe.config['ALLOWED_THUMBNAIL_EXTENSIONS'] = {'jpg', 'png', 'webp'}
cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'] = 'static/profile/pfp'
cafe.config['ALLOWED_PROFILE_PICTURE_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif'}
cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'] = 'static/profile/banner'
cafe.config['ALLOWED_PROFILE_BANNER_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif'}

# Ensure the directories for these folders exist
os.makedirs(cafe.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'], exist_ok=True)


def allowedFiletypes(filename, allowedExtensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowedExtensions


def connect_to_database():
    conn = sqlite3.connect("cafeDatabase.db")
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn


@cafe.route('/')
def indexPage():
    conn = sqlite3.connect('cafeDatabase.db')
    conn.execute('PRAGMA foreign_keys = ON')
    cursor = conn.cursor()
    username = session.get("username")
    userID = session.get("userID")

    # Fetch the latest videos for the new videos feed
    cursor.execute("""
            SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor
            FROM videos
            JOIN accounts ON videos.userID = accounts.userID
            JOIN profiles ON profiles.userID = accounts.userID
            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
            ORDER BY videoID DESC  -- Shows newest first
        """)
    videos = cursor.fetchall()  # List of tuples

    if username:
        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()
    else:
        profilePicture = ["profilepicturetest.png"]
    conn.close()
    return render_template('index.html', username=username, videos=videos, userID=userID,
                           time_ago=time_ago, profilePicture=profilePicture)


@cafe.route('/login')
def loginPage():
    return render_template('login.html')


@cafe.route('/loginAuth', methods=['GET', 'POST'])
def loginAuthAPI():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        conn = connect_to_database()
        conn.execute('PRAGMA foreign_keys = ON')
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
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    success, message = createAccount.createAccount(username, hashed_password)

    if success:
        session['username'] = username
        return redirect(url_for("logout"))
    else:
        return render_template("login.html", error=message)


@cafe.route('/logout')
def logout():
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
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor 
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        return render_template("upload.html", username=username, userID=session.get("userID"), profilePicture=profilePicture)
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
            thumbnailFilename = secure_filename(thumbnail.filename)
            thumbnailPath = os.path.join(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], thumbnailFilename)
            thumbnail.save(thumbnailPath)
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
    videoID = request.args.get('v')
    session['redirectToVideoID'] = videoID
    username = session.get('username')
    userID = session.get('userID')

    if videoID:
        # Retrieve video details
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()
        cursor.execute("""SELECT * 
                                FROM videos 
                                JOIN profiles ON profiles.userID = videos.userID
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE videoID = ?""", (videoID,))
        video = cursor.fetchone()

        if video:
            # If there is a video go to the video
            # Fetch the latest videos for the new videos feed
            cursor.execute("SELECT views FROM videos WHERE videoID = ?", (videoID,))
            viewCount = cursor.fetchone()
            viewCount = viewCount[0]
            if viewCount:
                viewCount = viewCount + 1
                currentViewCount = viewCount
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
                            SELECT comments.commentID, accounts.username, comments.comment, profiles.profilePicture, profileColorSets.profilePictureBorderColor
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            JOIN profiles ON profiles.userID = accounts.userID
                            JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                            WHERE videoID = ? 
                            ORDER BY commentID DESC 
                        """, (videoID,))
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
            datePublished = time_ago(timestamp)

            if username:
                cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID,))
                profilePicture = cursor.fetchone()
            else:
                profilePicture = ["profilepicturetest.png"]

            return render_template('watch.html', video=video, username=username, videos=videos,
                                   creatorUsername=creatorUsername, comments=comments, userID=userID,
                                   creatorUserID=video[1], num_of_comments=num_of_comments,
                                   currentViewCount=currentViewCount, num_of_subscribers=num_of_subscribers,
                                   isSubscribedToChannel=isSubscribedToChannel, num_of_likes=num_of_likes,
                                   isLikedVideo=isLikedVideo, datePublished=datePublished, time_ago=time_ago, profilePicture=profilePicture)
        else:
            return "Video not found", 404
    else:
        return "VideoID is required", 400


@cafe.route('/postComment', methods=["POST"])
def sendComment():
    if request.method == "POST":
        userID = session.get("userID")
        videoID = session.get("redirectToVideoID")

        comment = request.form["postComment"]

        post.sendCommentToDatabase(videoID, userID, comment)

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
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()

        # Fetch the latest videos for the new videos feed
        cursor.execute("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle, videos.views, videos.videoThumbnail, videos.datetime, profiles.profilePicture, profileColorSets.profilePictureBorderColor
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    JOIN profiles ON profiles.userID = accounts.userID
                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                    WHERE videos.videoTitle LIKE ?
                    ORDER BY videoID DESC  -- Shows newest first
                """, (searchQueryForDB,))
        videos = cursor.fetchall()  # List of tuples

        print(videos)

        num_of_videos = len(videos)

        if username:
            cursor.execute("""
                                    SELECT profilePicture, profileColorSets.profilePictureBorderColor
                                    FROM profiles 
                                    JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                    WHERE userID = ?""", (userID,))
            profilePicture = cursor.fetchone()
        else:
            profilePicture = ["profilepicturetest.png"]

        conn.close()
        return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos,
                               num_of_videos=num_of_videos, userID=userID, time_ago=time_ago, profilePicture=profilePicture)
    else:
        return redirect(url_for("indexPage"))


@cafe.route('/profile')
def getAccountProfile():
    userID = request.args.get('id')
    username = session.get("username")
    userID_session = session.get("userID")

    if userID:
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
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

            if username:
                cursor.execute("""
                                        SELECT profilePicture, profileColorSets.profilePictureBorderColor
                                        FROM profiles 
                                        JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                        WHERE userID = ?""", (userID_session,))
                profilePicture = cursor.fetchone()
            else:
                profilePicture = ["profilepicturetest.png"]

            return render_template("profile.html", username=username, profileDetails=profileDetails, videos=videos,
                                   userID=userID_session, time_ago=time_ago, profilePicture=profilePicture)
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(url_for("indexPage"))


@cafe.route('/subscribeUser')
def subscribeToUser():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    creatorUserID = request.args.get('creatorID')
    subscriberUserID = session["userID"]

    if int(creatorUserID) != int(subscriberUserID):
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
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
            conn.close()
            return redirect(request.referrer)
    else:
        return redirect(request.referrer)


@cafe.route('/likeVideo')
def likeVideoFromCreatorID():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    videoID = request.args.get('videoID')
    creatorUserID = request.args.get('creatorID')
    userID = session["userID"]

    if int(creatorUserID) != int(userID):
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
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
                conn.close()
                return redirect(request.referrer)
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(request.referrer)


@cafe.route('/editProfile')
def editUserProfile():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileBanner, profileColorSets.profilePictureBorderColor 
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profileInfo = cursor.fetchone()

        cursor.execute('SELECT profileSetID, profileSetName FROM profileColorSets')
        profileColorSets = cursor.fetchall()

        return render_template("edit_profile.html", username=username, userID=userID, profileInfo=profileInfo,
                               profileColorSets=profileColorSets)
    else:
        return redirect(url_for('indexPage'))


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
        conn = sqlite3.connect('cafeDatabase.db')
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()

        cursor.execute("""
                                SELECT profilePicture, profileColorSets.profilePictureBorderColor
                                FROM profiles 
                                JOIN profileColorSets ON profiles.profileColorTheme = profileColorSets.profileSetID
                                WHERE userID = ?""", (userID,))
        profilePicture = cursor.fetchone()

        return render_template('404.html', username=username, userID=userID, profilePicture=profilePicture), 404
    else:
        return render_template('404.html'), 404


cafe.run("127.0.0.1", 5000, debug=True)
