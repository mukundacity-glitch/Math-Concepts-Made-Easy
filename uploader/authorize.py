"""One-time YouTube authorization — run this on your own computer.

    1. Put your OAuth client file at  secrets/client_secret.json
       (Google Cloud Console → APIs & Services → Credentials →
        Create OAuth client ID → Desktop app, with the
        "YouTube Data API v3" enabled on the project).
    2. Run:  python -m uploader.authorize
    3. A browser window opens — sign in with the Google account that
       owns the Math Concepts Made Easy channel and click Allow.
    4. secrets/token.json is created. Uploads now work locally.
       For GitHub Actions, paste the contents of the two files into
       the repository secrets YT_CLIENT_SECRET_JSON and YT_TOKEN_JSON.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from uploader.youtube_upload import CLIENT_SECRET_PATH, TOKEN_PATH, SCOPES


def main():
    if not CLIENT_SECRET_PATH.exists():
        raise SystemExit(
            f"🛑 {CLIENT_SECRET_PATH} not found.\n"
            "   Create a Desktop-app OAuth client in Google Cloud Console\n"
            "   (with YouTube Data API v3 enabled) and save it there first."
        )
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"✅ Authorized. Token saved to {TOKEN_PATH}")
    print("   You can now run:  python autopilot.py --upload")


if __name__ == "__main__":
    main()
