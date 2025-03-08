import sqlite3


def uploadVideoToDatabase(userID, title, description, videoTags, filename):
    conn = sqlite3.connect('cafeDatabase.db')

    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO videos (userID, videoTitle, videoDescription, videoTags, videoFile) VALUES (?, ?, ?, ?, ?)",
                       (userID, title, description, videoTags, filename))
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
