import sqlite3
from datetime import datetime

import config

# Set the location for database path
cafeDatabasePath = config.sqlite_db_path


def createAccount(username, hashed_password):
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        cursor.execute("SELECT userID FROM accounts WHERE username = ?", (username,))
        userID = cursor.fetchone()
        joinDate = datetime.today()
        formatted_joinDate = joinDate.strftime("%d/%m/%Y")
        cursor.execute("INSERT INTO profiles (userID, joinDate, profileColorTheme, channelURLEnabled, channelURL) VALUES (?, ?, ?, ?, ?)", (userID[0], formatted_joinDate, 5, 0, username))
        conn.commit()
        cursor.execute("INSERT INTO playlists (userID, playlistName, playlistType, visibilityType) VALUES (?, ?, ?, ?)", (userID[0], f"{username}'s Saved Videos", "watch_queue", "Private"))
        conn.commit()
        print("Account created")
        return True, "Account created successfully!" # Return success message
    except sqlite3.IntegrityError:
        return False, "Username already exists" # Return error message
    finally:
        conn.close()
