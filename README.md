# cafeVideo
A lofi cafe-themed video sharing platform, designed for local or community instances.

## Project status
cafeVideo is an actively developed, experimental video-sharing application. The current codebase includes account registration and login, profile and theme customization, video upload and playback, comments and reactions, subscriptions, playlists and saves, notifications, admin account suspension, and invite-only Corners with public profiles and discovery.

The application is still under development. Features and interfaces may change, and the project has not been assessed or prepared for production use. The integration suite checks every currently registered GET and POST route and exercises important end-to-end workflows; this does not establish that every behavior, deployment environment, security control, privacy obligation, or regulatory requirement is complete.

Anyone obtaining, modifying, deploying, or operating the software is responsible for assessing its suitability and addressing the requirements applicable to their use. The project is provided under the Apache License, Version 2.0; this notice does not replace or modify the license or any applicable statutory rights or obligations.


## AI Disclosure
AI coding assistants have been used to explore the codebase, generate and modify application code, troubleshoot issues, and write or update tests and documentation. This includes implementation work on application features and interface changes; AI use has therefore gone beyond explanations or occasional code suggestions.

The project author provides direction, reviews and tests proposed changes, and decides what to integrate. AI-generated output can be incomplete or incorrect, and the project has not been independently audited. The author remains responsible for the project and its releases.

## Automated tests
GitHub Actions runs the Flask integration suite on pull requests targeting `main`, pushes to `main`, and manual dispatch. Tests use a temporary copy of the bundled database and Flask's test client to check anonymous and authenticated route behavior, account registration and login, uploads, profile editing, video interactions, playlists, notifications, Corners, admin suspension, and video API/streaming routes. Test uploads are cleaned up after each run.

To run the suite locally, install the application requirements and `pytest`, set `SECRET_CAFE_KEY`, then run:

```shell
python -m pytest -v .github/workflows/github_actions.py
```

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) and [NOTICE](NOTICE) files for details.
