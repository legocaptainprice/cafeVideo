from flask import Flask, render_template, request, url_for, session, jsonify, redirect, flash, abort, send_file
import hmac
import os
import re
import secrets
import sql_commands
import config
import manifest
import markdown
import mimetypes
from time_converter import time_ago, getVideoDatetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from werkzeug.middleware.proxy_fix import ProxyFix
from numberSimplifier import viewSimplify
from waitress import serve
from pathlib import Path

cafe = Flask(__name__)

cafe.config['UPLOAD_FOLDER'] = 'static/videos/'
cafe.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}
cafe.config['UPLOAD_THUMBNAILS_FOLDER'] = 'static/thumbnails'
cafe.config['ALLOWED_THUMBNAIL_EXTENSIONS'] = {'jpg', 'png', 'webp', 'jpeg', 'avif', 'jxl'}
cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'] = 'static/profile/pfp'
cafe.config['ALLOWED_PROFILE_PICTURE_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif', 'jpeg', 'avif', 'jxl'}
cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'] = 'static/profile/banner'
cafe.config['ALLOWED_PROFILE_BANNER_EXTENSIONS'] = {'jpg', 'png', 'webp', 'gif', 'jpeg', 'avif', 'jxl'}

# Ensure the directories for these folders exist
os.makedirs(cafe.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'], exist_ok=True)
os.makedirs(cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'], exist_ok=True)

# Security related features
cafe.config.update(
    SESSION_COOKIE_HTTPONLY=config.session_cookie_httponly,
    SESSION_COOKIE_SECURE=config.session_cookie_secure,  # Enable if hosting publicly
    SESSION_COOKIE_SAMESITE=config.session_cookie_samesite
)
cafeSecretKey = os.getenv("SECRET_CAFE_KEY")  # You MUST set a secret key in your environment variables

# Determine whether the host is using http or https
cafe.wsgi_app = ProxyFix(cafe.wsgi_app, x_proto=1, x_host=1)

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


def read_markdown_files(markdown_file, mode):
    with open(markdown_file, "r", encoding="utf-8") as file:
        content = file.read()

        if mode == "markdown":
            markdown_content = markdown.markdown(content)
            return markdown_content
        else:
            return content


def corner_csrf_token():
    return session.setdefault("corner_csrf_token", secrets.token_urlsafe(32))


def validate_corner_csrf():
    submittedToken = request.form.get("csrf_token", "")
    sessionToken = session.get("corner_csrf_token", "")
    if not sessionToken or not hmac.compare_digest(submittedToken, sessionToken):
        abort(400)


def render_corner_profile(corner):
    userID = session.get("userID")
    members = sql_commands.fetch_corner_members(corner["cornerID"])
    memberIDs = {member["userID"] for member in members}
    return render_template(
        "corner_profile.html",
        username=session.get("username"),
        userID=userID,
        corner=corner,
        members=members,
        isCornerCreator=userID == corner["userID"],
        isCornerMember=userID in memberIDs if userID is not None else False,
        corner_csrf_token=corner_csrf_token()
    )


def redirect_to_corner(cornerID):
    corner = sql_commands.fetch_corner_by_id(cornerID)
    if not corner:
        abort(404)
    if corner["cornerURLEnabled"] and corner["cornerURL"]:
        return redirect(url_for("cornerProfileByURL", cornerURL=corner["cornerURL"]))
    return redirect(url_for("cornerProfileByID", id=cornerID))


def require_admin():
    userID = session.get("userID")

    if userID is None:
        abort(403)

    userRole = sql_commands.fetch_user_role(userID)
    if not userRole or userRole["roleName"] != "Admin":
        abort(403)

    return userID


@cafe.context_processor
def global_variables():
    """Return the necessary data that will likely be used in all pages"""
    username = session.get("username")
    userID = session.get("userID")

    season, season_state = sql_commands.fetch_season_state()

    if username:
        profilePicture = sql_commands.fetch_profile_info("minimal", userID)
        featureAccess = sql_commands.fetch_account_info("feature_access", userID)
        subscriptionsInfo = sql_commands.fetch_subscription_info(userID)
        notifications, notificationsCount = sql_commands.fetch_user_notifications("minimal", userID)
        userRole = sql_commands.fetch_user_role(userID)

        return {
            "webTitle": manifest.WEB_TITLE,
            "season": season,
            "season_state": season_state,
            "profilePicture": profilePicture,
            "featureAccess": featureAccess,
            "subscriptionsInfo": subscriptionsInfo,
            "notifications": notifications,
            "notificationsCount": notificationsCount,
            "userRole": userRole
        }
    else:
        return {
            "webTitle": manifest.WEB_TITLE,
            "season": season,
            "season_state": season_state,
            "profilePicture": ["profilepicturetest.png"],
            "notifications:": [],
            "notificationsCount": 0
        }


@cafe.route('/')
def indexPage():
    """The home page for cafeVideo"""
    username = session.get("username")
    userID = session.get("userID")

    if username:
        # Fetch the latest videos for the subscriptions feed
        subscription_videos = sql_commands.fetch_subscription_videos("latest", userID)

        recommended_videos = sql_commands.fetch_user_recommended_feed(userID)

        return render_template('index.html', username=username, userID=userID,
                               time_ago=time_ago, subscription_videos=subscription_videos,
                               recommended_videos=recommended_videos)
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/login')
def loginPage():
    """Displays the login page to the user by rendering the login page template"""
    username = session.get("username")

    page_type = "Login"

    sql_commands.fetch_video_showcase_board()

    if username:
        return redirect(url_for("indexPage"))
    else:
        return render_template('login.html', page_type=page_type)


@cafe.route('/register')
def registerPage():
    """Displays the register page to the user by rendering the login page template"""
    username = session.get("username")

    page_type = "Register"

    sql_commands.fetch_video_showcase_board()

    if username:
        return redirect(url_for("indexPage"))
    else:
        return render_template('login.html', page_type=page_type)


@cafe.route('/loginAuth', methods=['GET', 'POST'])
def loginAuthAPI():
    """Handles the login authentication by checking the username and password to see if it matches a record on the
    database"""
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        # Fetch user from accounts table
        user = sql_commands.login_auth_check(username)

        # Check if user and password is correct
        if user and check_password_hash(user["password"], password):
            session['userID'] = user['userID']  # Store userID in session
            session['username'] = user['username']  # Store username in session
            return redirect(url_for("indexPage"))

        return cafe.redirect(url_for('loginPage', error="Invalid username or password"))

    return redirect(url_for("loginPage"))


@cafe.route('/registerAccount', methods=['POST'])
def registerAccountAPI():
    """Handles the registration process of the account by creating a new user record on the database"""
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    # Call the createAccount function and create the account with the username and hashed password
    success, message = sql_commands.createAccount(username, hashed_password)

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

        accountStanding = sql_commands.fetch_account_standing(userID)

        return render_template("upload.html", username=username, userID=userID,
                               accountStanding=accountStanding)
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/uploadVideo', methods=['POST'])
def uploadVideo():
    """Function to retrieve video details"""
    userID = session.get("userID")
    if userID is None:
        return redirect(url_for("loginPage"))
    if sql_commands.fetch_account_standing(userID) != "Active":
        abort(403)

    if request.method == 'POST':
        videoFile = request.files.get("video")
        if videoFile is None:
            return 'No file part', 400
        if videoFile.filename == '':
            return 'No selected file', 400
        if not allowedFiletypes(videoFile.filename, cafe.config['ALLOWED_EXTENSIONS']):
            return 'Unsupported video file type', 400

        thumbnail = request.files.get("thumbnail")
        defaultThumbnail = 'videotemplate.png'
        thumbnailFilename = defaultThumbnail
        if thumbnail and thumbnail.filename:
            if not allowedFiletypes(thumbnail.filename, cafe.config['ALLOWED_THUMBNAIL_EXTENSIONS']):
                return 'Unsupported thumbnail file type', 400
            thumbnailFilename = secure_filename(thumbnail.filename)

        filename = secure_filename(videoFile.filename)
        filepath = os.path.join(cafe.config['UPLOAD_FOLDER'], filename)
        videoFile.save(filepath)
        if thumbnail and thumbnail.filename:
            thumbnailPath = os.path.join(cafe.config['UPLOAD_THUMBNAILS_FOLDER'], thumbnailFilename)
            thumbnail.save(thumbnailPath)

        title = request.form['title']
        description = request.form['description']
        videoTags = request.form['videoTags']
        success, message = sql_commands.uploadVideoToDatabase(
            userID, title, description, videoTags, filename, thumbnailFilename
        )

        if success:
            return redirect(url_for('indexPage'))
        return render_template('upload.html', error=message)


@cafe.route('/watch')
def watchPage():
    """Function to display the watch page"""
    videoID = request.args.get('v')
    username = session.get('username')
    userID = session.get('userID')

    if videoID:

        video, accountStanding = sql_commands.fetch_video_for_watch_page(videoID)

        print(video)

        if video:
            session['redirectToVideoID'] = videoID
            # If there is a video go to the video
            viewCount = sql_commands.fetch_video_view_count_for_watch_page(videoID)

            if viewCount:
                viewCount = viewCount + 1
                currentViewCount = viewSimplify(viewCount)
                sql_commands.update_video_view_count(viewCount, videoID)
            else:
                addFirstView = 1
                sql_commands.update_video_view_count(addFirstView, videoID)
                currentViewCount = addFirstView

            creatorUsername = sql_commands.fetch_username(video[1])
            videos = sql_commands.fetch_latest_videos()

            comments = sql_commands.fetch_comments_section(session.get("userID"), videoID)
            num_of_comments = len(comments)
            subscribers = sql_commands.fetch_subscribers_count_from_creator(video[1])
            num_of_subscribers = len(subscribers)

            isSubscribedToChannel = sql_commands.check_user_subscribed_to_creator_channel(session.get("userID"),
                                                                                          video[1])
            if isSubscribedToChannel:
                isSubscribedToChannel = isSubscribedToChannel[0]

            likes = sql_commands.fetch_video_likes_for_watch_page(videoID)
            num_of_likes = len(likes)

            isLikedVideo = sql_commands.check_user_liked_video(videoID, session.get("userID"))
            if isLikedVideo:
                isLikedVideo = isLikedVideo[0]

            timestamp = int(video[6])
            datePublished = getVideoDatetime(timestamp)

            if username:
                sql_commands.sendWatchedVideoToDatabase(userID, videoID)  # Add video to user's watch history

                user_account_standing = sql_commands.fetch_account_standing(userID)

                # Fetch the playlists created by the user
                userPlaylists = sql_commands.fetch_user_playlists(userID)

                isVideoSaved = sql_commands.fetch_watch_page_details("saves", userID, videoID)

            else:
                userPlaylists = []
                user_account_standing = None
                isVideoSaved = False

            return render_template('watch.html', video=video, username=username, videos=videos,
                                   creatorUsername=creatorUsername, comments=comments, userID=userID,
                                   creatorUserID=video[1], num_of_comments=num_of_comments,
                                   currentViewCount=currentViewCount, num_of_subscribers=num_of_subscribers,
                                   isSubscribedToChannel=isSubscribedToChannel, num_of_likes=num_of_likes,
                                   isLikedVideo=isLikedVideo, datePublished=datePublished, time_ago=time_ago,
                                   viewSimplifier=viewSimplify, userPlaylists=userPlaylists, isVideoSaved=isVideoSaved,
                                   accountStanding=accountStanding, user_account_standing=user_account_standing)
        else:
            return "Video not found", abort(404)
    else:
        return "VideoID is required", abort(404)


@cafe.route('/postComment', methods=["POST"])
def sendComment():
    if request.method == "POST":
        if "userID" in session:
            userID = session.get("userID")
            videoID = session.get("redirectToVideoID")

            comment = request.form["postComment"]

            sql_commands.sendCommentToDatabase(videoID, userID, comment)

            return redirect(f'/watch?v={videoID}')
        else:
            return redirect(url_for('loginPage'))


@cafe.route('/postReply', methods=["POST"])
def sendReply():
    if request.method == "POST":
        if "userID" in session:
            userID = session.get("userID")
            videoID = session.get("redirectToVideoID")
            commentID = session.get("replyToCommentID")

            reply = request.form["postReply"]

            sql_commands.sendReplyToDatabase(commentID, userID, reply)

            return redirect(f'/watch?v={videoID}')
        else:
            return redirect(url_for('loginPage'))


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

        videos = sql_commands.fetch_search_results("Regular", searchQueryForDB, "None")

        num_of_videos = len(videos)

        if username:
            subscription_videos = sql_commands.fetch_search_results("Subscriptions", searchQueryForDB, userID)
            num_of_subscription_videos = len(subscription_videos)
            return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos,
                                   num_of_videos=num_of_videos, userID=userID, time_ago=time_ago,
                                   subscription_videos=subscription_videos,
                                   num_of_subscription_videos=num_of_subscription_videos)
        else:
            return render_template("search.html", searchQuery=searchQuery, username=username, videos=videos,
                                   num_of_videos=num_of_videos, userID=userID, time_ago=time_ago)

    else:
        return redirect(url_for("indexPage"))


@cafe.route('/channel')
def getAccountProfile():
    userID = request.args.get('id')
    username = session.get("username")
    userID_session = session.get("userID")

    if userID:

        # Check if the userID exists
        foundUserID = sql_commands.validate_userID(userID)

        if foundUserID:
            profileDetails = sql_commands.fetch_profile_info("profilePage", userID)

            accountStanding = sql_commands.fetch_account_standing(userID)

            # Fetch the latest videos for the new videos feed
            videos = sql_commands.fetch_profile_info("latestVideos", userID)
            num_of_videos = len(videos)

            subscribers = sql_commands.fetch_subscribers_count_from_creator(userID)
            num_of_subscribers = len(subscribers)

            # Fetch the channel's user role if it has any
            channelHasRole = sql_commands.fetch_user_role(userID)

            if username:
                profilePicture = sql_commands.fetch_profile_info("minimal", userID_session)
                subscriptionsInfo = sql_commands.fetch_subscription_info(userID_session)

                isSubscribedToChannel = sql_commands.check_user_subscribed_to_creator_channel(userID_session, userID)

                if isSubscribedToChannel:
                    isSubscribedToChannel = isSubscribedToChannel[0]

                notifications, notificationsCount = sql_commands.fetch_user_notifications("minimal", userID_session)

                if accountStanding == "Suspended" and str(userID_session) != str(userID):
                    return render_template('account_suspended.html', username=username, userID=userID_session,
                                           profilePicture=profilePicture, notifications=notifications,
                                           subscriptionsInfo=subscriptionsInfo, notificationsCount=notificationsCount)
                else:
                    return render_template("profile.html", username=username, profileDetails=profileDetails,
                                           videos=videos,
                                           userID=userID_session, time_ago=time_ago, profilePicture=profilePicture,
                                           num_of_subscribers=num_of_subscribers, subscriptionsInfo=subscriptionsInfo,
                                           channelID=userID, isSubscribedToChannel=isSubscribedToChannel,
                                           num_of_videos=num_of_videos, notifications=notifications,
                                           notificationsCount=notificationsCount, channelHasRole=channelHasRole,
                                           accountStanding=accountStanding)

            else:
                if accountStanding == "Suspended":
                    return render_template('account_suspended.html')
                else:
                    return render_template("profile.html", username=username, profileDetails=profileDetails,
                                           videos=videos, userID=userID_session, time_ago=time_ago,
                                           num_of_subscribers=num_of_subscribers, channelID=userID,
                                           num_of_videos=num_of_videos, channelHasRole=channelHasRole,
                                           accountStanding=accountStanding)
        else:
            return redirect(url_for("indexPage"))
    else:
        return redirect(url_for("indexPage"))


@cafe.route('/<channelURL>')
def redirectPage(channelURL):
    """The profile of the user by their channel URL"""
    viewerUserID = session.get('userID')
    viewerUsername = session.get("username")

    channelURLEnabled = sql_commands.check_channelURL_status(channelURL)

    try:
        if channelURLEnabled[0] == 1:
            userID = sql_commands.fetch_profile_from_channelURL(channelURL)
            userID = userID[0]
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

        isSubscribed = sql_commands.check_user_subscribed_to_creator_channel(subscriberUserID, creatorUserID)

        if isSubscribed:
            sql_commands.remove_user_subscription(subscriberUserID, creatorUserID)
            return redirect(request.referrer)
        else:
            sql_commands.add_user_subscription(subscriberUserID, creatorUserID)

            # Send the notification to the database

            usernameOfSubscriber = sql_commands.fetch_username(subscriberUserID)

            sql_commands.sendNotificationToDatabase(creatorUserID, subscriberUserID,
                                            f"{usernameOfSubscriber[0]} has subscribed to your channel", "",
                                            "subscribedToChannel", "None")

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

        videoExists = sql_commands.check_video_exists(videoID)

        if videoExists:

            isLikedVideo = sql_commands.check_video_liked(videoID, creatorUserID, userID)

            if isLikedVideo:
                sql_commands.delete_like_from_video(videoID, creatorUserID, userID)
                print("User has unliked the video")
                return redirect(request.referrer)
            else:
                sql_commands.add_like_to_video(videoID, creatorUserID, userID)

                usernameOfLiker = sql_commands.fetch_username(userID)

                videoTitle = sql_commands.fetch_video_title(videoID)

                sql_commands.sendNotificationToDatabase(creatorUserID, userID, f"{usernameOfLiker[0]} liked your video",
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

        commentExists = sql_commands.fetch_video_comment(commentID)

        if commentExists:

            isLikedComment = sql_commands.check_comment_liked(commentID, commenterID, userID)

            if isLikedComment:
                sql_commands.delete_comment_like(commentID, commenterID, userID)
                return redirect(request.referrer)
            else:
                sql_commands.add_comment_like(commentID, commenterID, userID)

                # Send the notification to the database

                usernameOfLiker = sql_commands.fetch_username(userID)
                print(usernameOfLiker[0])

                # Cutting corners here for a sec

                sql_commands.sendNotificationToDatabase(commenterID, userID, f"{usernameOfLiker[0]} has liked your comment",
                                                "", "likedComment", "None")
                return redirect(request.referrer)
        else:
            return redirect(url_for('indexPage'))
    else:
        return redirect(request.referrer)


@cafe.route('/likeReply', methods=["POST"])
def likeReplyFromReplierID():
    if "userID" not in session:
        return redirect(url_for('loginPage'))

    replyID = request.args.get("replyID")
    replierID = request.args.get("replierID")
    userID = session["userID"]

    if int(replierID) != int(userID):

        replyExists = sql_commands.fetch_video_reply(replyID)

        if replyExists:

            isLikedReply = sql_commands.check_reply_liked(replyID, replierID, userID)

            if isLikedReply:
                sql_commands.delete_reply_like(replyID, replierID, userID)
                return redirect(request.referrer)
            else:
                sql_commands.add_reply_like(replyID, replierID, userID)
                return redirect(request.referrer)
        else:
            return redirect(url_for('indexPage'))
    else:
        return redirect(request.referrer)


@cafe.route('/account/profile/edit')
def editUserProfile():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        profilePicture = sql_commands.fetch_profile_info("extended", userID)

        # Need to also add a way to have some hidden themes only available for certain events
        # This can be done by adding a hidden column to the profileColorSets table
        profileColorSets = sql_commands.fetch_profile_color_sets()

        return render_template("edit_profile.html", username=username, userID=userID, profilePicture=profilePicture,
                               profileColorSets=profileColorSets)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/account/settings')
def getAccountSettings():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        profilePicture = sql_commands.fetch_profile_info("extended", userID)

        profileColorSets = sql_commands.fetch_profile_color_sets()

        # Fetch the amount of features the user has access to
        userAccessList = sql_commands.fetch_user_feature_access(userID)

        accountStanding = sql_commands.fetch_account_standing(userID)

        if userAccessList:
            userAccessDisplay = []
            for userAccess in userAccessList:
                feature = sql_commands.fetch_user_features(userAccess[0])
                userAccessDisplay.append(feature)
        else:
            userAccessDisplay = False

        return render_template("account_settings.html", username=username, userID=userID, profilePicture=profilePicture,
                               profileColorSets=profileColorSets, userAccessDisplay=userAccessDisplay,
                               accountStanding=accountStanding)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/admin')
def adminPage():
    require_admin()
    session.setdefault("admin_csrf_token", secrets.token_urlsafe(32))

    return render_template(
        "admin.html",
        username=session.get("username"),
        accounts=sql_commands.fetch_admin_accounts(),
        admin_csrf_token=session["admin_csrf_token"]
    )


@cafe.route('/admin/users/<int:targetUserID>/suspend', methods=["POST"])
def suspendAccount(targetUserID):
    userID = require_admin()
    submittedToken = request.form.get("csrf_token", "")
    sessionToken = session.get("admin_csrf_token", "")

    if not sessionToken or not hmac.compare_digest(submittedToken, sessionToken):
        abort(400)

    if targetUserID == userID:
        flash("You cannot suspend your own account.", "error")
    elif sql_commands.suspend_user_account(targetUserID):
        flash("The account has been suspended.", "success")
    else:
        flash("The account was not found or is already suspended.", "error")

    return redirect(url_for("adminPage"))


@cafe.route('/confirmAccountEdit', methods=["POST"])
def confirmAccountDetailsEdit():
    if request.method == "POST":
        try:
            userID = session.get('userID')
        except:
            return redirect(url_for('indexPage'))
        username = request.form["usernameEdit"]
        channelURL = request.form["channelURL"]

        success, message = sql_commands.changeAccountDetailsConfirm(userID, username, channelURL)

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

        if profilePicture and allowedFiletypes(profilePicture.filename,
                                               cafe.config['ALLOWED_PROFILE_PICTURE_EXTENSIONS']):
            profilePictureFilename = secure_filename(profilePicture.filename)
            profilePicturePath = os.path.join(cafe.config['UPLOAD_PROFILE_PICTURE_FOLDER'], profilePictureFilename)
            profilePicture.save(profilePicturePath)

            successfulProfilePictureUpload, message = sql_commands.uploadProfilePictureToDatabase(profilePictureFilename,
                                                                                          userID)
            if successfulProfilePictureUpload:
                success = True

        if profileBanner and allowedFiletypes(profileBanner.filename, cafe.config['ALLOWED_PROFILE_BANNER_EXTENSIONS']):
            profileBannerFilename = secure_filename(profileBanner.filename)
            profileBannerPath = os.path.join(cafe.config['UPLOAD_PROFILE_BANNER_FOLDER'], profileBannerFilename)
            profileBanner.save(profileBannerPath)

            successfulProfileBannerUpload, message = sql_commands.uploadProfileBannerToDatabase(profileBannerFilename, userID)
            if successfulProfileBannerUpload:
                success = True

        if bio != '':
            success, message = sql_commands.sendProfileBioToDatabase(bio, userID)

        if profileColorTheme != '':
            success, message = sql_commands.updateProfileColorTheme(profileColorTheme, userID)

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

        return render_template('404.html', username=username, userID=userID), 404
    else:
        return render_template('404.html'), 404


@cafe.errorhandler(405)
def pageForbidden(error):
    return pageNotFound(NotFound)


@cafe.errorhandler(500)
def pageErrorOccurred(error):
    username = session.get('username')
    userID = session.get('userID')

    if username:

        return render_template('500.html', username=username, userID=userID), 500
    else:
        return render_template('500.html'), 500


@cafe.route('/subscriptions')
def accountSubscriptions():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        videos = sql_commands.fetch_subscription_videos("page", userID)

        return render_template('subscriptions.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago)
    else:
        return redirect(url_for('indexPage'))


@cafe.route('/explore')
def explorePage():
    username = session.get("username")
    userID = session.get("userID")

    # Fetch the latest videos for the new videos feed
    videos = sql_commands.fetch_latest_videos()

    trending_videos = sql_commands.fetch_explore_trending_feed()

    if username:

        return render_template('explore.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, trending_videos=trending_videos)
    else:
        profilePicture = ["profilepicturetest.png"]
        notifications = []
    return render_template('explore.html', username=username, videos=videos, userID=userID,
                           time_ago=time_ago, profilePicture=profilePicture, notifications=notifications,
                           trending_videos=trending_videos)


@cafe.route("/likes/videos")
def likedVideosPage():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        # Fetch the latest videos for the liked videos section
        videos = sql_commands.fetch_user_liked_videos(userID)

        return render_template('liked_videos.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago)
    else:
        return redirect(url_for('loginPage'))


@cafe.route("/history/videos")
def watchHistory():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        # Fetch the latest videos for the watch history section
        videos = sql_commands.fetch_user_watch_history(userID)

        return render_template('history.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago)
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/playlists/videos')
def userPlaylist():
    username = session.get("username")
    userID = session.get("userID")

    if username:

        # Fetch the playlists created by the user
        userPlaylists = sql_commands.fetch_user_playlists(userID)

        return render_template('playlists.html', username=username, userPlaylists=userPlaylists, userID=userID,
                               time_ago=time_ago)
    else:
        return redirect(url_for('loginPage'))


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

        if playlistName:
            sql_commands.create_video_playlist(userID, playlistName, playlistDescription, "Regular", playlistVisibility)

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

    playlistIDFound = sql_commands.fetch_user_playlist(playlistID)

    if playlistIDFound:
        print(f"Playlist ID: {playlistIDFound[0]} has been found!\nPlaylist Title: {playlistIDFound[2]}")

        print(playlistIDFound[2])

        # Fetch the latest videos for the playlist section

        videos = sql_commands.fetch_user_playlist_videos(playlistID)

        return render_template('playlist.html', username=username, videos=videos, userID=userID,
                               time_ago=time_ago, playlistInfo=playlistIDFound, watch_queue=False)
    else:
        abort(404)


@cafe.route('/saves')
def viewSaves():
    username = session.get('username')
    userID = session.get('userID')

    if username:
        playlistIDFound = sql_commands.fetch_user_saves_playlist(userID, "watch_queue")

        if playlistIDFound:
            print(f"Playlist ID: {playlistIDFound[0]} has been found!\nPlaylist Title: {playlistIDFound[2]}")

            print(playlistIDFound[2])

            # Fetch the latest videos for the playlist section
            videos = sql_commands.fetch_user_saved_videos(playlistIDFound[0])

            return render_template('playlist.html', username=username, videos=videos, userID=userID,
                                   time_ago=time_ago, playlistInfo=playlistIDFound, watch_queue=True)
        else:
            abort(404)
    else:
        return redirect(url_for('loginPage'))


@cafe.route('/about')
def aboutPage():
    username = session.get('username')
    userID = session.get('userID')

    WEB_TITLE = manifest.WEB_TITLE
    VERSION = f"{manifest.MAJOR}.{manifest.MINOR}.{manifest.PATCH}"
    CHANNEL = manifest.CHANNEL
    CODENAME = manifest.CODENAME
    COPYRIGHT = manifest.COPYRIGHT

    if username:

        return render_template('about.html', username=username, userID=userID, WEB_TITLE=WEB_TITLE,
                               VERSION=VERSION, CODENAME=CODENAME, CHANNEL=CHANNEL, COPYRIGHT=COPYRIGHT)
    else:
        return render_template('about.html', WEB_TITLE=WEB_TITLE,
                               VERSION=VERSION, CODENAME=CODENAME, CHANNEL=CHANNEL, COPYRIGHT=COPYRIGHT)


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
def cornersPage():
    username = session.get("username")
    userID = session.get("userID")

    if username:
        corners = sql_commands.fetch_corners_for_user(userID)
        cornerMembers = sql_commands.fetch_corner_card_members(
            [corner["cornerID"] for corner in corners]
        )
        return render_template(
            'corners.html',
            username=username,
            userID=userID,
            corners=corners,
            corner_members=cornerMembers
        )
    else:
        return redirect(url_for('cornersExplore'))


@cafe.route('/corners/explore')
def cornersExplore():
    corners = sql_commands.fetch_corners_for_explore()
    return render_template(
        "corners_explore.html",
        username=session.get("username"),
        userID=session.get("userID"),
        corners=corners,
        corner_members=sql_commands.fetch_corner_card_members(
            [corner["cornerID"] for corner in corners]
        )
    )


@cafe.route('/corner/create', methods=["GET", "POST"])
def cornerCreate():
    userID = session.get("userID")
    username = session.get("username")
    if userID is None or not username:
        return redirect(url_for("loginPage"))

    if request.method == "POST":
        validate_corner_csrf()
        if sql_commands.fetch_account_standing(userID) in (None, "Suspended"):
            abort(403)

        cornerName = request.form.get("cornerName", "").strip()
        cornerDescription = request.form.get("cornerDescription", "").strip()
        cornerURLEnabled = request.form.get("cornerURLEnabled") == "on"
        cornerURL = request.form.get("cornerURL", "").strip().lower()

        if not cornerName or len(cornerName) > 80 or len(cornerDescription) > 500:
            flash("Enter a Corner name (up to 80 characters) and description (up to 500 characters).", "error")
        elif cornerURLEnabled and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", cornerURL):
            flash("Custom URLs can contain lowercase letters, numbers, and single hyphens between words.", "error")
        elif cornerURLEnabled and cornerURL in {"create", "corner", "join", "decline"}:
            flash("That custom URL is reserved for a Corner page.", "error")
        else:
            cornerID = sql_commands.create_corner(
                userID, cornerName, cornerDescription, cornerURLEnabled, cornerURL
            )
            if cornerID is None:
                flash("That custom Corner URL is already in use.", "error")
            else:
                flash("Your Corner has been created.", "success")
                return redirect_to_corner(cornerID)

    return render_template(
        "corner_create.html",
        username=username,
        userID=userID,
        corner_csrf_token=corner_csrf_token()
    )


@cafe.route('/corner/corner')
def cornerProfileByID():
    cornerID = request.args.get("id", type=int)
    if cornerID is None:
        abort(404)
    corner = sql_commands.fetch_corner_by_id(cornerID)
    if not corner:
        abort(404)
    if corner["cornerURLEnabled"] and corner["cornerURL"]:
        return redirect(url_for("cornerProfileByURL", cornerURL=corner["cornerURL"]))
    return render_corner_profile(corner)


@cafe.route('/corner/<cornerURL>')
def cornerProfileByURL(cornerURL):
    corner = sql_commands.fetch_corner_by_url(cornerURL)
    if not corner:
        abort(404)
    return render_corner_profile(corner)


@cafe.route('/corner/<int:cornerID>/invite', methods=["POST"])
def cornerInvite(cornerID):
    userID = session.get("userID")
    if userID is None:
        return redirect(url_for("loginPage"))
    validate_corner_csrf()
    if sql_commands.fetch_account_standing(userID) in (None, "Suspended"):
        abort(403)
    if sql_commands.fetch_corner_owner(cornerID) != userID:
        abort(403)

    invitedUsername = request.form.get("username", "").strip()
    result = sql_commands.create_corner_invitation(cornerID, userID, invitedUsername)
    messages = {
        "invited": ("Invitation sent.", "success"),
        "user_not_found": ("No active account was found with that username.", "error"),
        "already_member": ("That user is already a Corner member.", "error"),
        "already_invited": ("That user already has a pending invitation.", "error"),
        "not_owner": ("Only the Corner creator can invite members.", "error")
    }
    message, category = messages[result]
    flash(message, category)
    return redirect_to_corner(cornerID)


@cafe.route('/corner/join', methods=["POST"])
def cornerJoin():
    userID = session.get("userID")
    if userID is None:
        return redirect(url_for("loginPage"))
    validate_corner_csrf()
    cornerID = request.args.get("cornerID", type=int)
    if cornerID is None:
        abort(400)
    if sql_commands.fetch_account_standing(userID) == "Suspended":
        abort(403)
    if not sql_commands.accept_corner_invitation(userID, cornerID):
        flash("There is no pending invitation for that Corner.", "error")
        return redirect(url_for("notificationsPage"))
    return redirect_to_corner(cornerID)


@cafe.route('/corner/decline', methods=["POST"])
def cornerDeclineInvitation():
    userID = session.get("userID")
    if userID is None:
        return redirect(url_for("loginPage"))
    validate_corner_csrf()
    cornerID = request.args.get("cornerID", type=int)
    if cornerID is None:
        abort(400)
    if not sql_commands.decline_corner_invitation(userID, cornerID):
        flash("There is no pending invitation for that Corner.", "error")
    else:
        flash("Corner invitation declined.", "success")
    return redirect(url_for("notificationsPage"))


@cafe.route('/test/template/run')
def test_template():
    """This is for testing future and experimental pages"""
    if config.debug:
        username = session.get('username')
        userID = session.get('userID')

        if username:

            return render_template('notice.html', username=username, userID=userID)
        else:
            return render_template('notice.html')
    else:
        abort(404)


@cafe.route('/help/guidelines')
def guidelines_page():
    """This is for viewing the platform guidelines"""

    username = session.get('username')
    userID = session.get('userID')

    markdown_content = read_markdown_files("GUIDELINES.md", "markdown")

    if username:

        return render_template('guidelines.html', username=username, userID=userID,
                               markdown_content=markdown_content)
    else:
        return render_template('guidelines.html', markdown_content=markdown_content)


@cafe.route('/help/license')
def license_page():
    """This is for viewing cafeVideo's license"""

    username = session.get('username')
    userID = session.get('userID')

    markdown_content = read_markdown_files("LICENSE", "text")

    if username:

        return render_template('license.html', username=username, userID=userID,
                               markdown_content=markdown_content)
    else:
        return render_template('license.html', markdown_content=markdown_content)


@cafe.route('/help/notice')
def notice_page():
    """This is for viewing cafeVideo's notice"""

    username = session.get('username')
    userID = session.get('userID')

    markdown_content = read_markdown_files("NOTICE", "text")

    if username:

        return render_template('notice.html', username=username, userID=userID,
                               markdown_content=markdown_content)
    else:
        return render_template('notice.html', markdown_content=markdown_content)


@cafe.route('/notifications/all')
def notificationsPage():
    """This is page is for users managing their notifications"""

    username = session.get('username')
    userID = session.get('userID')

    if username:
        return render_template(
            'notifications.html',
            username=username,
            userID=userID,
            pending_corner_invitations=sql_commands.fetch_pending_corner_invitations(userID),
            corner_csrf_token=corner_csrf_token()
        )
    else:
        return render_template('notifications.html')


@cafe.route("/notifications/actions/read", methods=["POST"])
def notification_action_read():
    if request.method == "POST":
        userID = session.get('userID')

        if userID:
            notificationID = request.args.get('id')
            if notificationID:
                sql_commands.mark_notification_as_read(notificationID, userID)

                return redirect(request.referrer)
            else:
                abort(404)
        else:
            abort(404)
    else:
        abort(404)


@cafe.route("/api/videos/<int:videoID>", methods=["GET"])
def retrieve_video_api(videoID):
    """Returns the video data for the requested videoID"""

    video = sql_commands.fetch_video_api(videoID)

    if video:
        return {
            "videoID": video[0],
            "userID": video[1],
            "Title": video[2],
            "Description": video[3],
            "Tags": video[4],
            "uploadDate": video[6],
            "views": video[7]
        }
    else:
        abort(404)


@cafe.route("/api/videos/<int:videoID>/stream", methods=["GET"])
def retrieve_video_stream(videoID):
    """Retrieve the video file to stream"""

    video = sql_commands.fetch_video_api(videoID)

    if video:

        videoFile = Path(cafe.root_path) / "static" / "videos" / video[5]

        mime_type, _ = mimetypes.guess_type(videoFile.name)

        if not os.path.isfile(videoFile):
            abort(404)
        else:
            return send_file(
                videoFile,
                mimetype=mime_type,
                as_attachment=False,
                conditional=True
            )
    else:
        abort(404)


if __name__ == "__main__":
    if config.debug:
        cafe.run(config.ip_address, config.port, debug=config.debug)
    else:
        serve(cafe, listen=f"{config.ip_address}:{config.port}", threads=config.threads)
