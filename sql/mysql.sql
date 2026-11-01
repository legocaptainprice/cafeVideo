-- Import into an empty MySQL 8+ database using a client configured for utf8mb4.
-- User/account data is intentionally not seeded, only application reference data is.

CREATE TABLE accounts (
    userID BIGINT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin UNIQUE,
    password TEXT,
    email VARCHAR(320),
    accountStanding VARCHAR(32),
    verification VARCHAR(255),
    PRIMARY KEY (userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE profileColorSets (
    profileSetID BIGINT NOT NULL AUTO_INCREMENT,
    profileSetName VARCHAR(100),
    profileBorderColor VARCHAR(32),
    profileHeaderColor VARCHAR(32),
    profilePictureBorderColor VARCHAR(32),
    PRIMARY KEY (profileSetID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE roles (
    roleID BIGINT NOT NULL AUTO_INCREMENT,
    roleName VARCHAR(100),
    PRIMARY KEY (roleID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE events (
    eventID BIGINT NOT NULL AUTO_INCREMENT,
    eventName VARCHAR(100),
    eventCSSDir TEXT,
    eventHTMLDir TEXT,
    eventImagesDir TEXT,
    eventJSDir TEXT,
    PRIMARY KEY (eventID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE feature_gating (
    featureID BIGINT NOT NULL AUTO_INCREMENT,
    featureName VARCHAR(100),
    description TEXT,
    enabled SMALLINT,
    PRIMARY KEY (featureID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE season (
    eventState SMALLINT,
    eventID BIGINT,
    CONSTRAINT fk_season_event FOREIGN KEY (eventID) REFERENCES events(eventID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE profiles (
    userID BIGINT,
    displayName VARCHAR(255),
    profileBio TEXT,
    profilePicture VARCHAR(255),
    profileBanner VARCHAR(255),
    profileColorTheme BIGINT,
    joinDate VARCHAR(32),
    channelURLEnabled SMALLINT,
    channelURL VARCHAR(255),
    CONSTRAINT fk_profiles_account FOREIGN KEY (userID) REFERENCES accounts(userID),
    CONSTRAINT fk_profiles_color FOREIGN KEY (profileColorTheme) REFERENCES profileColorSets(profileSetID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE videos (
    videoID BIGINT NOT NULL AUTO_INCREMENT,
    userID BIGINT,
    videoTitle VARCHAR(255),
    videoDescription TEXT,
    videoTags TEXT,
    videoFile VARCHAR(255),
    datetime BIGINT,
    views BIGINT DEFAULT 0,
    videoThumbnail VARCHAR(255),
    PRIMARY KEY (videoID),
    CONSTRAINT fk_videos_account FOREIGN KEY (userID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE blogs (
    blogID BIGINT NOT NULL AUTO_INCREMENT,
    userID BIGINT,
    blogTitle VARCHAR(255),
    blogDescription TEXT,
    blogContent LONGTEXT,
    blogDatetime BIGINT,
    PRIMARY KEY (blogID),
    CONSTRAINT fk_blogs_account FOREIGN KEY (userID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE comments (
    commentID BIGINT NOT NULL AUTO_INCREMENT,
    videoID BIGINT,
    userID BIGINT,
    comment TEXT,
    PRIMARY KEY (commentID),
    CONSTRAINT fk_comments_video FOREIGN KEY (videoID) REFERENCES videos(videoID),
    CONSTRAINT fk_comments_account FOREIGN KEY (userID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE replies (
    replyID BIGINT NOT NULL AUTO_INCREMENT,
    commentID BIGINT,
    userID BIGINT,
    reply TEXT,
    PRIMARY KEY (replyID),
    CONSTRAINT fk_replies_comment FOREIGN KEY (commentID) REFERENCES comments(commentID),
    CONSTRAINT fk_replies_account FOREIGN KEY (userID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE playlists (
    playlistID BIGINT NOT NULL AUTO_INCREMENT,
    userID BIGINT,
    playlistName VARCHAR(255),
    playlistDescription TEXT,
    playlistType VARCHAR(64),
    visibilityType VARCHAR(32),
    PRIMARY KEY (playlistID),
    CONSTRAINT fk_playlists_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE playlist_contents (
    playlistID BIGINT NOT NULL,
    videoID BIGINT NOT NULL,
    PRIMARY KEY (playlistID, videoID),
    CONSTRAINT fk_playlist_contents_playlist FOREIGN KEY (playlistID) REFERENCES playlists(playlistID) ON DELETE CASCADE,
    CONSTRAINT fk_playlist_contents_video FOREIGN KEY (videoID) REFERENCES videos(videoID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE feature_access (
    featureID BIGINT,
    userID BIGINT,
    CONSTRAINT fk_feature_access_feature FOREIGN KEY (featureID) REFERENCES feature_gating(featureID),
    CONSTRAINT fk_feature_access_account FOREIGN KEY (userID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_roles (
    userID BIGINT,
    roleID BIGINT,
    CONSTRAINT fk_user_roles_account FOREIGN KEY (userID) REFERENCES accounts(userID),
    CONSTRAINT fk_user_roles_role FOREIGN KEY (roleID) REFERENCES roles(roleID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE subscriptions (
    userID BIGINT,
    subscribedToUserID BIGINT,
    CONSTRAINT fk_subscriptions_subscriber FOREIGN KEY (userID) REFERENCES accounts(userID),
    CONSTRAINT fk_subscriptions_creator FOREIGN KEY (subscribedToUserID) REFERENCES accounts(userID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE likedVideos (
    videoID BIGINT,
    creatorID BIGINT,
    userID BIGINT,
    CONSTRAINT fk_liked_videos_video FOREIGN KEY (videoID) REFERENCES videos(videoID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_videos_creator FOREIGN KEY (creatorID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_videos_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE likedComments (
    commentID BIGINT,
    commenterID BIGINT,
    userID BIGINT,
    CONSTRAINT fk_liked_comments_comment FOREIGN KEY (commentID) REFERENCES comments(commentID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_comments_commenter FOREIGN KEY (commenterID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_comments_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE likedReplies (
    replyID BIGINT,
    replierID BIGINT,
    userID BIGINT,
    CONSTRAINT fk_liked_replies_reply FOREIGN KEY (replyID) REFERENCES replies(replyID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_replies_replier FOREIGN KEY (replierID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_liked_replies_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE notifications (
    notificationID BIGINT NOT NULL AUTO_INCREMENT,
    notificationRecipientID BIGINT,
    notificationSenderID BIGINT,
    notificationTitle VARCHAR(255),
    notificationDescription TEXT,
    notificationDateTime BIGINT,
    notificationItem VARCHAR(255),
    notificationImage VARCHAR(255),
    notificationRead SMALLINT,
    PRIMARY KEY (notificationID),
    CONSTRAINT fk_notifications_recipient FOREIGN KEY (notificationRecipientID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_sender FOREIGN KEY (notificationSenderID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE watchHistory (
    userID BIGINT NOT NULL,
    videoID BIGINT NOT NULL,
    historyDateTime BIGINT,
    PRIMARY KEY (userID, videoID),
    CONSTRAINT fk_watch_history_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_watch_history_video FOREIGN KEY (videoID) REFERENCES videos(videoID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cafeCorners (
    cornerID BIGINT NOT NULL AUTO_INCREMENT,
    userID BIGINT NOT NULL,
    cornerName VARCHAR(255),
    cornerDescription TEXT,
    cornerBanner VARCHAR(255),
    cornerColorTheme BIGINT,
    cornerURLEnabled SMALLINT,
    cornerURL VARCHAR(255),
    creationDate BIGINT,
    PRIMARY KEY (cornerID),
    CONSTRAINT fk_cafe_corners_creator FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_cafe_corners_color FOREIGN KEY (cornerColorTheme) REFERENCES profileColorSets(profileSetID) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cafeCornerMembers (
    cornerID BIGINT NOT NULL,
    userID BIGINT NOT NULL,
    `role` VARCHAR(32) NOT NULL,
    joinedDate BIGINT,
    PRIMARY KEY (cornerID, userID),
    CONSTRAINT fk_cafe_corner_members_corner FOREIGN KEY (cornerID) REFERENCES cafeCorners(cornerID) ON DELETE CASCADE,
    CONSTRAINT fk_cafe_corner_members_account FOREIGN KEY (userID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cornerInvitations (
    invitationID BIGINT NOT NULL AUTO_INCREMENT,
    cornerID BIGINT NOT NULL,
    inviterUserID BIGINT NOT NULL,
    invitedUserID BIGINT NOT NULL,
    invitationStatus VARCHAR(32) NOT NULL DEFAULT 'pending',
    createdAt BIGINT NOT NULL,
    PRIMARY KEY (invitationID),
    CONSTRAINT fk_corner_invitations_corner FOREIGN KEY (cornerID) REFERENCES cafeCorners(cornerID) ON DELETE CASCADE,
    CONSTRAINT fk_corner_invitations_inviter FOREIGN KEY (inviterUserID) REFERENCES accounts(userID) ON DELETE CASCADE,
    CONSTRAINT fk_corner_invitations_invited FOREIGN KEY (invitedUserID) REFERENCES accounts(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO profileColorSets
    (profileSetID, profileSetName, profileBorderColor, profileHeaderColor, profilePictureBorderColor)
VALUES
    (1, 'Vaporwave', '#0097ec', '#b967ff', '#d569f6'),
    (2, 'Hike', '#bdc039', '#4a5933', '#c0ac3f'),
    (3, 'Hyperchill', '#f97698', '#6783db', '#ffb845'),
    (4, 'Coffee', '#d2691e', '#6F4E37', '#d2691e'),
    (5, 'Default', '#C78A4B', '#C78A4B', '#C78A4B'),
    (6, 'Strawberry Milk', '#fbe9e9', '#d84f4f', '#f9b5b5');

INSERT INTO roles (roleID, roleName)
VALUES (1, 'Staff'), (2, 'Developer'), (3, 'Moderator'), (4, 'Admin');

INSERT INTO events (eventID, eventName, eventCSSDir, eventHTMLDir, eventImagesDir, eventJSDir)
VALUES
    (1, 'halloween2026', 'css/events/halloween2026', 'events/halloween2026', 'images/events/halloween2026', 'js/events/halloween2026'),
    (2, 'christmas2026', 'css/events/christmas2026', 'events/christmas2026', 'images/events/christmas2026', 'js/events/christmas2026');

INSERT INTO feature_gating (featureID, featureName, description, enabled)
VALUES
    (1, 'Lattes', 'Testing out the portrait form of video coming to cafeVideo', 0),
    (2, 'commentSection_v2', 'A revamped comment section', 0);

INSERT INTO season (eventState, eventID) VALUES (0, 1);
