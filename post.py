import sqlite3
import time
from datetime import datetime

import config
import time_converter

# Set the location for the database path
cafeDatabasePath = config.sqlite_db_path


def uploadVideoToDatabase(userID, title, description, videoTags, filename, thumbnailFilename):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    datetimeOfPublishedVideo = int(time.time())

    cursor = conn.cursor()

    try:
        cursor.execute("""INSERT INTO videos (userID, videoTitle, videoDescription, videoTags, videoFile, 
                                videoThumbnail, datetime) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (userID, title, description, videoTags, filename, thumbnailFilename, datetimeOfPublishedVideo))
        conn.commit()
        print("Video uploaded")
        return True, "Video uploaded successfully"
    except sqlite3.IntegrityError:
        return False, "Video failed to upload"
    finally:
        cursor.close()
        conn.close()


def sendCommentToDatabase(videoID, userID, comment):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO comments (videoID, userID, comment) VALUES (?, ?, ?)", (videoID, userID, comment))
        conn.commit()

        # Send the notification to the database

        cursor.execute("SELECT username FROM accounts WHERE userID = ?", (userID,))
        usernameOfCommenter = cursor.fetchone()
        print(usernameOfCommenter[0])
        cursor.execute("SELECT userID FROM videos WHERE videoID = ?", (videoID,))
        creatorID = cursor.fetchone()

        if int(userID) != int(creatorID[0]):
            sendNotificationToDatabase(creatorID[0], userID, f"{usernameOfCommenter[0]} has commented on your video",
                                       "", "commentOnVideo", "None")

        print("Comment sent")
    except sqlite3.IntegrityError:
        print("Error with posting comment")
    finally:
        cursor.close()
        conn.close()


def sendReplyToDatabase(commentID, userID, reply):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO replies (commentID, userID, reply) VALUES (?, ?, ?)",
                       (commentID, userID, reply))
        conn.commit()
        print("Reply sent")
    except sqlite3.IntegrityError:
        print("Error with posting reply")
    finally:
        cursor.close()
        conn.close()


def uploadProfilePictureToDatabase(profilePictureFilename, userID):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE profiles SET profilePicture = ? WHERE userID = ?",
                       (profilePictureFilename, userID))
        conn.commit()
        return True, "Uploaded successfully"
    except sqlite3.IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        cursor.close()
        conn.close()


def uploadProfileBannerToDatabase(profileBannerFilename, userID):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE profiles SET profileBanner = ? WHERE userID = ?",
                       (profileBannerFilename, userID))
        conn.commit()
        return True, "Uploaded successfully"
    except sqlite3.IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        cursor.close()
        conn.close()


def sendProfileBioToDatabase(bio, userID):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE profiles SET profileBio = ? WHERE userID = ?",
                       (bio, userID))
        conn.commit()
        return True, "Uploaded successfully"
    except sqlite3.IntegrityError:
        print("Error with updating profile settings")
        return False, "Error with updating profile settings"
    finally:
        cursor.close()
        conn.close()


def updateProfileColorTheme(profileColorTheme, userID):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE profiles SET profileColorTheme = ? WHERE userID = ?', (profileColorTheme, userID))
        conn.commit()
        return True, "Profile Color Theme has been updated"
    except sqlite3.IntegrityError:
        return False, "Profile Color Theme failed to update"
    finally:
        cursor.close()
        conn.close()


def sendNotificationToDatabase(recipientID, senderID, title, description, item, image):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    notificationSent = int(time.time())

    try:
        cursor.execute("INSERT INTO notifications (notificationRecipientID, notificationSenderID, notificationTitle, "
                       "notificationDescription, notificationDateTime, notificationItem, notificationImage, "
                       "notificationRead) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (recipientID, senderID, title, description, notificationSent, item, image, 0))
        conn.commit()
        print("Notification sent")
    except sqlite3.IntegrityError:
        print("Error with sending notification")
    finally:
        cursor.close()
        conn.close()


def sendWatchedVideoToDatabase(userID, videoID):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    dateOfVideoWatched = int(time.time())

    try:
        cursor.execute("SELECT * FROM watchHistory WHERE userID = ? AND videoID = ?", (userID, videoID))
        videoWatched = cursor.fetchone()

        if videoWatched:
            cursor.execute("UPDATE watchHistory SET historyDateTime = ? WHERE userID = ? AND videoID = ?", (dateOfVideoWatched, userID, videoID))
            conn.commit()
        else:
            cursor.execute("INSERT INTO watchHistory (userID, videoID, historyDateTime) VALUES (?, ?, ?)", (userID, videoID, dateOfVideoWatched))
            conn.commit()
    except sqlite3.IntegrityError:
        print("Error when updating watch history")
    finally:
        cursor.close()
        conn.close()

