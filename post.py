import sqlite3
import time
from datetime import datetime
import time_converter


def uploadVideoToDatabase(userID, title, description, videoTags, filename, thumbnailFilename):
    conn = sqlite3.connect('cafeDatabase.db')
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
    conn = sqlite3.connect('cafeDatabase.db')

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
