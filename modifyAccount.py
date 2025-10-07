import sqlite3

# Set location for database path
cafeDatabasePath = 'cafeDatabase.db'


def changeAccountDetailsConfirm(userID, username, channelURL):
    """This is for changing account details e.g. username, channel URL, etc"""
    conn = sqlite3.connect(cafeDatabasePath)
    conn.execute('PRAGMA foreign_keys = ON')

    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE accounts SET username = ? WHERE userID = ?", (username, userID,))
        conn.commit()
        # Check if channelURL is enabled
        cursor.execute("SELECT channelURLEnabled FROM profiles WHERE userID = ?", (userID,))
        channelURLStatus = cursor.fetchone()
        print(channelURLStatus[0])
        # Check if new channelURL does not already exist
        cursor.execute("SELECT channelURL FROM profiles WHERE UPPER(channelURL) = UPPER(?)", (channelURL,))
        channelURLExist = cursor.fetchone()
        print(channelURLExist)
        # If the channelURL does not exist then update the user's channelURL
        if not channelURLExist:
            cursor.execute("UPDATE profiles SET channelURL = ? WHERE userID = ?", (channelURL, userID))
            conn.commit()
            # Enable channelURL if its not enabled
            if channelURLStatus[0] == 0:
                cursor.execute("UPDATE profiles SET channelURLEnabled = ? WHERE userID = ?", (1, userID))
                conn.commit()
        else:
            print(f"Channel URL, {channelURLExist}, already exists")
            # If the channelURL does exist and the channelURL is not enabled
            if channelURLStatus[0] == 0:
                cursor.execute("SELECT * FROM profiles WHERE UPPER(channelURL) = UPPER(?) AND userID = ?", (channelURL, userID))
                # Check if the channelURL matches the userID of the user saving the changes
                channelURL_Matches_UserID = cursor.fetchone()
                # Enable channelURL if its not enabled
                if channelURL_Matches_UserID:
                    cursor.execute("UPDATE profiles SET channelURLEnabled = ? WHERE userID = ?", (1, userID))
                    conn.commit()
        return True, "Account details updated successfully"
    except sqlite3.IntegrityError:
        return False, "Account details failed to update"
    finally:
        cursor.close()
        conn.close()


