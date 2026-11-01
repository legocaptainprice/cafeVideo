import os


# cafeVideo Metadata
WEB_TITLE = "cafeVideo"
MAJOR = 1
MINOR = 0
PATCH = 0
CODENAME = "Coral Reef"
CHANNEL = "alpha"
BUILD_NUMBER = int(os.environ.get("CAFE_BUILD_NUMBER", "0"))
GITHUB_LINK = "https://github.com/legocaptainprice/cafeVideo"
COPYRIGHT = "Copyright © 2025-2026 legocaptainprice"

CHANNELS = {"alpha", "beta", "rc", "release"}


def full_version(build_number=BUILD_NUMBER, channel=CHANNEL):
    base_version = f"{MAJOR}.{MINOR}.{PATCH}"
    if channel not in CHANNELS:
        raise ValueError(f"Unsupported release channel: {channel}")
    channel_name = channel.lower()
    return f"{base_version}.build{build_number}.{channel_name}"


def display_version(build_number=BUILD_NUMBER, channel=CHANNEL):
    return full_version(build_number, channel)


def release_tag(build_number=BUILD_NUMBER, channel=CHANNEL):
    return f"v{full_version(build_number, channel)}"


FULL_VERSION = full_version()
DISPLAY_VERSION = display_version()
