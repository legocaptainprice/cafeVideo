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
GitHub Actions runs the Flask integration suite on pull requests targeting `main`, pushes to `main`, and manual dispatch. Tests use a temporary copy of the bundled database and Flask's test client to check anonymous and authenticated route behavior, account registration and login, uploads, profile editing, video interactions, playlists, notifications, Corners, admin suspension, and video API/streaming routes. Test uploads are cleaned up after each run.

To run the suite locally, install the application requirements and `pytest`, set `SECRET_CAFE_KEY`, then run:

```shell
python -m pytest -v .github/workflows/github_actions.py
```

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) and [NOTICE](NOTICE) files for details.
