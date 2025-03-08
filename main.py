from flask import Flask, render_template, request, url_for, session, jsonify, redirect
import sqlite3, createAccount, post, os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

cafe = Flask(__name__)
cafe.secret_key = "supersecretkey"

cafe.config['UPLOAD_FOLDER'] = 'static/videos/'
cafe.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}


def allowedFiletypes(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in cafe.config['ALLOWED_EXTENSIONS']


def connect_to_database():
    conn = sqlite3.connect("cafeDatabase.db")
    conn.row_factory = sqlite3.Row
    return conn


@cafe.route('/')
def indexPage():
    conn = sqlite3.connect('cafeDatabase.db')
    cursor = conn.cursor()

    # Fetch the latest videos for the new videos feed
    cursor.execute("""
            SELECT videos.videoID, accounts.username, videos.videoTitle
            FROM videos
            JOIN accounts ON videos.userID = accounts.userID
            ORDER BY videoID DESC  -- Shows newest first
        """)
    videos = cursor.fetchall()  # List of tuples
    conn.close()
    return render_template('index.html', username=session.get("username"), videos=videos, userID=session.get("userID"))


@cafe.route('/login')
def loginPage():
    return render_template('login.html')


@cafe.route('/loginAuth', methods=['GET', 'POST'])
def loginAuthAPI():
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

    # If the user is not logged in, send them to the login page
    if username:
        return render_template("upload.html", username=username, userID=session.get("userID"))
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/uploadVideo', methods=['POST'])
def uploadVideo():
    """Function to retrieve video details"""
    if request.method == 'POST':
        if 'video' not in request.files:
            return 'No file part', 400
        file = request.files['video']

        if file.filename == '':
            return 'No selected file', 400

        if file and allowedFiletypes(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(cafe.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            userID = session.get('userID')
            print(userID)
            title = request.form['title']
            description = request.form['description']
            videoTags = request.form['videoTags']
            # videoFile = request.form['videoURL']

            success, message = post.uploadVideoToDatabase(userID, title, description, videoTags, filename)

            if success:
                return redirect(url_for('indexPage'))
            else:
                return render_template('upload.html', error=message)


@cafe.route('/watch')
def watchPage():
    videoID = request.args.get('v')
    session['redirectToVideoID'] = videoID
    username = session.get('username')

    if videoID:
        # Retrieve video details
        conn = sqlite3.connect('cafeDatabase.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE videoID = ?", (videoID,))
        video = cursor.fetchone()

        if video:
            # If there is a video go to the video
            # Fetch the latest videos for the new videos feed
            cursor.execute("SELECT username FROM accounts WHERE userID = ?", (video[1],))
            creatorUsername = cursor.fetchone()
            cursor.execute("""
                            SELECT videos.videoID, accounts.username, videos.videoTitle
                            FROM videos
                            JOIN accounts ON videos.userID = accounts.userID
                            ORDER BY videoID DESC  -- Shows newest first
                        """)
            videos = cursor.fetchall()  # List of tuples
            cursor.execute("""
                            SELECT comments.commentID, accounts.username, comments.comment
                            FROM comments
                            JOIN accounts ON comments.userID = accounts.userID
                            WHERE videoID = ? 
                            ORDER BY commentID DESC 
                        """, (videoID,))
            comments = cursor.fetchall()
            return render_template('watch.html', video=video, username=username, videos=videos,
                                   creatorUsername=creatorUsername, comments=comments, userID=session.get("userID"))
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

    if searchQuery:
        conn = sqlite3.connect('cafeDatabase.db')
        cursor = conn.cursor()

        # Fetch the latest videos for the new videos feed
        cursor.execute("""
                    SELECT videos.videoID, accounts.username, videos.videoTitle
                    FROM videos
                    JOIN accounts ON videos.userID = accounts.userID
                    WHERE videos.videoTitle LIKE ?
                    ORDER BY videoID DESC  -- Shows newest first
                """, (searchQueryForDB,))
        videos = cursor.fetchall()  # List of tuples

        num_of_videos = len(videos)

        conn.close()
        return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos, num_of_videos=num_of_videos, userID=session.get("userID"))
    else:
        return redirect(url_for("indexPage"))


@cafe.route('/profile')
def getAccountProfile():
    userID = request.args.get('id')
    username = session.get("username")

    if userID:
        conn = sqlite3.connect('cafeDatabase.db')
        cursor = conn.cursor()

        # Check if the userID exists
        cursor.execute("SELECT * FROM accounts WHERE userID = ?", (userID,))
        foundUserID = cursor.fetchone()

        if foundUserID:
            cursor.execute("""
                                SELECT * 
                                FROM accounts 
                                JOIN profiles ON accounts.userID = profiles.userID
                                WHERE accounts.userID = ?
                                """, (userID,))
            profileDetails = cursor.fetchone()

            # Fetch the latest videos for the new videos feed
            cursor.execute("""
                                SELECT videos.videoID, accounts.username, videos.videoTitle
                                FROM videos
                                JOIN accounts ON videos.userID = accounts.userID
                                WHERE videos.userID = ?
                                ORDER BY videoID DESC  -- Shows newest first
                            """, (userID,))
            videos = cursor.fetchall()  # List of tuples

            return render_template("profile.html", username=username, profileDetails=profileDetails, videos=videos, userID=session.get("userID"))
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(url_for("indexPage"))


cafe.run("127.0.0.1", 5000, debug=True)
