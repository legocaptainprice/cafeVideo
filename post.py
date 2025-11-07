import sqlite3
import time
from datetime import datetime
import time_converter

# Set the location for the database path
cafeDatabasePath = 'cafeDatabase.db'


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
