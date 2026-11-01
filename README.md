# cafeVideo
A lofi cafe-themed video sharing platform, designed for local or community instances.

## Project status
cafeVideo is a very early-stage, actively developed, experimental video-sharing application. The current codebase includes account registration and login, profile and theme customization, video upload and playback, comments and reactions, subscriptions, playlists and saves, notifications, admin account suspension, and invite-only Corners with public profiles and discovery.

The application is still under development. Features and interfaces may change, and the project has not been assessed or prepared for public or production use. Many safeguards, processes, and compliance measures that may be required for a publicly hosted instance are incomplete, unverified, or not implemented. This includes, among other things, data protection, data collection transparency and controls, privacy, security, moderation, data retention and deletion, and requirements that vary by jurisdiction. The integration suite checks every currently registered GET and POST route and exercises important end-to-end workflows; it does not establish that the application is safe, compliant, or suitable for public deployment.

The software is provided as an experimental code project, not as a hosted service or a representation that it is ready for public deployment or legally compliant. Anyone obtaining, modifying, deploying, or operating it is responsible for independently assessing its suitability and implementing the safeguards and meeting the legal obligations applicable to their use. Operators should obtain qualified advice where appropriate before making the application publicly available. This description is informational, not legal advice, and does not replace or modify the Apache License, Version 2.0, or any applicable statutory rights or obligations.


## AI Disclosure
The project is developed through a combination of code written by the project author and AI-assisted coding. AI coding assistants have also been used to explore the codebase, generate and modify application code, troubleshoot issues, and write or update tests and documentation. This includes implementation work on application features and interface changes; AI use has therefore gone beyond explanations or occasional code suggestions.

The project author provides direction, reviews and tests proposed changes, decides what to integrate, and performs human moderation. AI-generated output can be incomplete or incorrect, and the project has not been independently audited.

## Automated tests
GitHub Actions runs the Flask integration suite on pull requests targeting `main`, pushes to `main`, and manual dispatch. It exercises anonymous and authenticated routes and major account, upload, profile, video, playlist, notification, Corner, admin, API, and streaming flows. CI runs the same suite against a temporary SQLite database and disposable MySQL and PostgreSQL services; test uploads are cleaned up after each run.

To run the suite locally, install the application requirements and `pytest`, set `SECRET_CAFE_KEY`, then run:

```shell
python -m pytest -v .github/workflows/github_actions.py
```

## Versioning and builds
`manifest.py` defines the current version and release channel (`alpha`, `beta`, `rc`, or `release`). A successful build on `main` uses the commit's position in the complete `main` history as its monotonically increasing build number; with 114 commits currently on `main`, the next single commit there will build as `1.0.0.build115.alpha`. Changing channels does not reset the number. The same no-space version string is shown in the app and used for the artifact name, for example `cafeVideo-1.0.0.build115.alpha.zip`. Pull requests and other branches do not create builds.

Every successful main-branch build uploads a versioned artifact. Alpha builds do not create GitHub Releases. Beta and release-candidate (`rc`) builds create prereleases, while `release` builds create regular GitHub Releases; each release includes its matching artifact. Pull requests run tests but do not publish artifacts or releases.

## Database engines
SQLite remains the default and uses the bundled `cafeDatabase.db`. Full initial schemas and required reference data for MySQL 8+ and PostgreSQL are provided in `sql/mysql.sql` and `sql/postgresql.sql`; import the appropriate script into a new, empty database before running the application. These scripts include the platform's required profile color themes, roles, seasonal events, feature flags, and current season, but intentionally do not create user accounts.

Set `CAFE_DATABASE_URL` to a SQLAlchemy URL to select a different database engine. Install the matching SQLAlchemy driver (`python -m pip install PyMySQL` for `mysql+pymysql://...`, or `python -m pip install "psycopg[binary]"` for `postgresql+psycopg://...`). For example:

```powershell
$env:CAFE_DATABASE_URL = "mysql+pymysql://user:password@localhost/cafevideo?charset=utf8mb4"
# or
$env:CAFE_DATABASE_URL = "postgresql+psycopg://user:password@localhost/cafevideo"
```

Keep credentials out of source control. The bundled SQLite database remains unchanged; the SQL scripts are for new MySQL/PostgreSQL installations rather than migrations of existing databases.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) and [NOTICE](NOTICE) files for details.
