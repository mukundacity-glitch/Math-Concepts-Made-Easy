"""Upload the day's finished lesson (long video + Short) to YouTube.

    python -m uploader.youtube_upload --day 1 --dry-run   # preview metadata
    python -m uploader.youtube_upload --day 1             # real upload

Credentials (one-time setup, see README):
  secrets/client_secret.json  OAuth client from Google Cloud Console
  secrets/token.json          created by:  python -m uploader.authorize
In CI the same two files are provided through the environment
variables YT_CLIENT_SECRET_JSON and YT_TOKEN_JSON (raw JSON content).

Videos default to PRIVATE so you can review the first uploads. Set
YT_PRIVACY=public (or pass --privacy public) once you trust the output.
"""

import argparse
import json
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.paths import BASE_DIR, safe_filename
from pipeline.curriculum import get_lesson

SECRETS_DIR = REPO_ROOT / "secrets"
CLIENT_SECRET_PATH = SECRETS_DIR / "client_secret.json"
TOKEN_PATH = SECRETS_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

CHANNEL_TAGLINE = "New math lessons every day on Math Concepts Made Easy."

# 3 Shorts a day, each a different type, spread across the day so the
# channel posts multiple times without dumping everything at once.
# Times are UTC-of-day on the actual upload date. Order: morning teaser
# → pre-video formula reveal (the main lesson video goes out around
# 19:00 UTC) → evening CTA.
SHORTS_SCHEDULE_UTC = {
    "HOOK":    time(12, 0),
    "FORMULA": time(18, 0),
    "MISTAKE": time(22, 0),
}

SHORT_TYPE_META = {
    "HOOK":    {"tag": "#DidYouKnow", "blurb": "Bet you didn't know this about"},
    "FORMULA": {"tag": "#MathHack",   "blurb": "The one formula you need for"},
    "MISTAKE": {"tag": "#MathMistake","blurb": "Stop making this mistake in"},
}


def compute_publish_at(short_key: str) -> Optional[str]:
    """ISO 8601 UTC publishAt for a Short's scheduled slot *today* (the
    calendar day this upload actually runs on), or None if that slot has
    already passed today (upload immediately instead). Anchored to the
    real run date rather than the lesson's nominal day number so the 3
    Shorts always land spread across whichever day they're posted."""
    slot_time = SHORTS_SCHEDULE_UTC[short_key]
    now = datetime.now(timezone.utc)
    publish_dt = datetime.combine(now.date(), slot_time, tzinfo=timezone.utc)
    if publish_dt <= now:
        return None
    return publish_dt.isoformat().replace("+00:00", "Z")


def _materialize_env_secrets():
    """In CI, write YT_*_JSON env vars to the expected secret files."""
    SECRETS_DIR.mkdir(exist_ok=True)
    for env_name, path in [("YT_CLIENT_SECRET_JSON", CLIENT_SECRET_PATH),
                           ("YT_TOKEN_JSON", TOKEN_PATH)]:
        value = os.environ.get(env_name)
        if value and not path.exists():
            path.write_text(value, encoding="utf-8")


def credentials_available() -> bool:
    _materialize_env_secrets()
    return CLIENT_SECRET_PATH.exists() and TOKEN_PATH.exists()


def get_service():
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    except json.JSONDecodeError as e:
        raise SystemExit(
            "🛑 YouTube token file is not valid JSON — the YT_TOKEN_JSON "
            "repository secret is malformed (most likely it has extra "
            "content pasted after the closing '}', e.g. two copies of "
            "secrets/token.json concatenated together, or extra "
            "whitespace/text appended).\n"
            "   Fix: open secrets/token.json locally (created by "
            "`python -m uploader.authorize`), copy its *exact* contents, "
            "and replace the YT_TOKEN_JSON repository secret with that — "
            "nothing more, nothing less.\n"
            f"   Original error: {e}"
        ) from e
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise SystemExit(
                "🛑 YouTube token refresh failed — the stored refresh token "
                "was rejected (expired or revoked).\n"
                "   This almost always means the Google Cloud OAuth consent "
                "screen is still in 'Testing' status: Google auto-expires "
                "refresh tokens after 7 days for apps in that mode.\n"
                "   Fix: Google Cloud Console → APIs & Services → OAuth "
                "consent screen → publish the app to 'In production' (no "
                "Google verification needed for a personal/unlisted channel "
                "tool), then re-run `python -m uploader.authorize` once and "
                "update the YT_TOKEN_JSON repository secret with the new "
                "secrets/token.json.\n"
                f"   Original error: {e}"
            ) from e
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


# ══════════════════════════════════════════════════════════════
# METADATA — built entirely from curriculum data, never hard-coded
# ══════════════════════════════════════════════════════════════

# 3-5 hashtags per subject area — more does not improve ranking
GEOMETRY_SUBJECTS = {"Triangles", "Quadrilaterals", "Circles", "Coordinate Geometry"}
ALGEBRA_SUBJECTS = {"Polynomials", "Linear Equations", "Quadratic Equations",
                    "Sequences and Series"}


def grade_label(lesson: dict) -> str:
    subject = lesson.get("subject", "")
    if "SAT" in subject:
        return "SAT Math"
    if "ACT" in subject:
        return "ACT Math"
    grade = lesson.get("grade")
    return f"Grade {grade} Math" if grade else "High School Math"


def build_title(lesson: dict) -> str:
    """SEO title formula: topic promise | grade + 'Full Lesson' | day.
    Falls back to shorter forms instead of truncating mid-word (YouTube
    caps titles at 100 characters)."""
    for title in (
        f"{lesson['seo_title']} | {grade_label(lesson)} Full Lesson | Day {lesson['day']}",
        f"{lesson['seo_title']} | {grade_label(lesson)} | Day {lesson['day']}",
        f"{lesson['seo_title']} | Day {lesson['day']}",
    ):
        if len(title) <= 100:
            return title
    return lesson["seo_title"][:100]


def build_hashtags(lesson: dict) -> list:
    subject = lesson.get("subject", "")
    if subject in GEOMETRY_SUBJECTS:
        return ["#Geometry", "#HighSchoolGeometry", "#MathHelp",
                "#LearnGeometry", "#MathConceptsMadeEasy"]
    if subject in ALGEBRA_SUBJECTS:
        return ["#Algebra", "#Algebra1", "#HighSchoolMath",
                "#LearnAlgebra", "#MathConceptsMadeEasy"]
    grade = lesson.get("grade")
    grade_tag = [f"#Grade{grade}Math"] if grade else ["#HighSchoolMath"]
    return ["#MathConceptsMadeEasy"] + grade_tag + ["#LearnMath", "#MathTutorial"]


def build_description(lesson: dict) -> str:
    lines = [
        f"Day {lesson['day']} — {lesson['topic']}: {lesson['subtopic']}",
        "",
        f"🎯 What you will learn: {lesson['lesson_goal']}",
        f"📖 Prerequisite: {lesson['prerequisite']}",
        f"🧮 Key idea (spoken): {lesson['formula_spoken']}",
        "",
        lesson.get("concept_intuition", ""),
        "",
        f"⚠️ Common mistake we fix in this lesson: {lesson.get('common_mistake', '')}",
        "",
        f"📚 Track: {lesson['global_track']} → {lesson['subject']} → {lesson['concept_cluster']}",
        f"🎓 Useful for: {', '.join(lesson.get('exam_tags', []))}",
        "",
        f"Perfect for {grade_label(lesson)} students — covers Grade 9 math, "
        "Grade 10 math, Algebra 1, high school math, Common Core math, "
        "homework help, math tutoring, and math exam preparation, with clear "
        "step-by-step examples and practice in every lesson.",
        "",
        CHANNEL_TAGLINE,
        "",
        " ".join(build_hashtags(lesson)),
    ]
    return "\n".join(lines)


def build_tags(lesson: dict) -> list:
    tags = [
        "math", "mathematics", "learn math", "math made easy",
        lesson["subject"], lesson["topic"], lesson["concept_cluster"],
        lesson["global_track"] + " math",
        "grade 9 math", "grade 10 math", "algebra 1", "high school math",
        "common core math", "homework help", "math tutoring",
        "math exam preparation", "math concepts explained",
    ] + [f"{tag} math" for tag in lesson.get("exam_tags", [])]
    return list(dict.fromkeys(t.strip() for t in tags if t.strip()))[:30]


def lesson_paths(lesson: dict) -> dict:
    day = lesson["day"]
    safe = safe_filename(lesson["seo_title"])
    final_dir = BASE_DIR / "final_videos"
    return {
        "video": final_dir / f"Day_{day:03d}_{safe}.mp4",
        "shorts": {
            key: final_dir / f"Day_{day:03d}_{safe}_SHORT_{key}.mp4"
            for key in SHORTS_SCHEDULE_UTC
        },
        "thumbnail": BASE_DIR / "thumbnails" / f"Day_{day:03d}_{safe}_Thumb.jpg",
        "srt": final_dir / f"Day_{day:03d}_{safe}.srt",
    }


def build_short_title(lesson: dict, short_key: str) -> str:
    meta = SHORT_TYPE_META[short_key]
    for title in (
        f"{meta['blurb']} {lesson['topic']} {meta['tag']} #Shorts",
        f"{lesson['thumbnail_angle']} {meta['tag']} #Shorts",
        f"{lesson['seo_title']} #Shorts",
    ):
        if len(title) <= 100:
            return title
    return lesson["seo_title"][:95] + " #Shorts"


def build_short_description(lesson: dict, short_key: str) -> str:
    meta = SHORT_TYPE_META[short_key]
    return (
        f"Day {lesson['day']} — {lesson['topic']}: {lesson['subtopic']}\n\n"
        f"{lesson['formula_spoken']}\n\n"
        f"Full lesson on the channel. {CHANNEL_TAGLINE}\n\n"
        f"#Shorts #math #learnmath {meta['tag']}"
    )


# ══════════════════════════════════════════════════════════════
# UPLOAD STEPS
# ══════════════════════════════════════════════════════════════

def _upload_file(service, path: Path, title: str, description: str,
                 tags: list, privacy: str, publish_at: str = None) -> str:
    from googleapiclient.http import MediaFileUpload

    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at and privacy == "public":
        # Only schedule when the caller actually wants this public — YouTube
        # requires "private" at upload time for publishAt to take effect,
        # then flips it public automatically at that timestamp. Leaving a
        # requested private/unlisted video alone respects that choice.
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status,
    }
    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   ⬆️  {path.name}: {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"   ✅ Uploaded → https://youtu.be/{video_id}")
    return video_id


def _set_thumbnail(service, video_id: str, thumb: Path):
    try:
        service.thumbnails().set(videoId=video_id, media_body=str(thumb)).execute()
        print(f"   ✅ Thumbnail set → {thumb.name}")
    except Exception as e:  # custom thumbnails need a verified channel
        print(f"   ⚠️  Thumbnail not set ({e}). Verify the channel at "
              f"youtube.com/verify to enable custom thumbnails.")


def _upload_captions(service, video_id: str, srt: Path):
    try:
        from googleapiclient.http import MediaFileUpload
        service.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": "en",
                              "name": "English", "isDraft": False}},
            media_body=MediaFileUpload(str(srt)),
        ).execute()
        print(f"   ✅ Captions uploaded → {srt.name}")
    except Exception as e:
        print(f"   ⚠️  Captions not uploaded ({e}).")


def _add_to_playlist(service, video_id: str, playlist_name: str):
    try:
        playlists, page = {}, None
        while True:
            resp = service.playlists().list(part="snippet", mine=True,
                                            maxResults=50, pageToken=page).execute()
            for item in resp.get("items", []):
                playlists[item["snippet"]["title"]] = item["id"]
            page = resp.get("nextPageToken")
            if not page:
                break
        playlist_id = playlists.get(playlist_name)
        if not playlist_id:
            resp = service.playlists().insert(part="snippet,status", body={
                "snippet": {"title": playlist_name,
                            "description": CHANNEL_TAGLINE},
                "status": {"privacyStatus": "public"},
            }).execute()
            playlist_id = resp["id"]
            print(f"   ✅ Created playlist → {playlist_name}")
        service.playlistItems().insert(part="snippet", body={
            "snippet": {"playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video",
                                       "videoId": video_id}},
        }).execute()
        print(f"   ✅ Added to playlist → {playlist_name}")
    except Exception as e:
        print(f"   ⚠️  Playlist step failed ({e}).")


def upload_day(day: int, dry_run: bool = False, privacy: str = None):
    lesson = get_lesson(day)
    paths = lesson_paths(lesson)
    privacy = privacy or os.environ.get("YT_PRIVACY", "private")

    title = build_title(lesson)
    description = build_description(lesson)
    tags = build_tags(lesson)
    short_meta = {
        key: {
            "title": build_short_title(lesson, key),
            "description": build_short_description(lesson, key),
            "publish_at": compute_publish_at(key),
        }
        for key in SHORTS_SCHEDULE_UTC
    }

    print(f"\n{'═' * 65}")
    print(f"  📤 YOUTUBE UPLOAD — Day {day}: {lesson['topic']}")
    print(f"  🔒 Privacy: {privacy}{'  (DRY RUN)' if dry_run else ''}")
    print(f"{'═' * 65}")
    print(f"  Title    : {title}")
    print(f"  Playlist : {lesson['playlist']}")
    print(f"  Tags     : {', '.join(tags[:8])}…")
    print(f"  Video    : {paths['video']}")
    for key, short_path in paths["shorts"].items():
        if privacy != "public":
            slot = f"immediately as {privacy} (scheduling only applies to public)"
        else:
            slot = short_meta[key]["publish_at"] or "now (slot already passed)"
        print(f"  Short {key:7s}: {short_path.name}  → publishes {slot}")

    if dry_run:
        print("\n── Description preview " + "─" * 40)
        print(description)
        print("\n✅ Dry run complete — nothing was uploaded.")
        return

    if not paths["video"].exists():
        raise SystemExit(f"🛑 Final video not found: {paths['video']} — "
                         f"run autopilot.py first.")

    if not credentials_available():
        raise SystemExit(
            "🛑 YouTube is not linked yet. Follow README → "
            "'Linking your YouTube channel', then re-run this command.")

    service = get_service()

    print("\n▶ Uploading main lesson…")
    video_id = _upload_file(service, paths["video"], title, description, tags, privacy)
    if paths["thumbnail"].exists():
        _set_thumbnail(service, video_id, paths["thumbnail"])
    if paths["srt"].exists():
        _upload_captions(service, video_id, paths["srt"])
    _add_to_playlist(service, video_id, lesson["playlist"])

    for key, short_path in paths["shorts"].items():
        if not short_path.exists():
            print(f"\n⚠️  Short {key} not found ({short_path.name}) — skipping.")
            continue
        meta = short_meta[key]
        print(f"\n▶ Uploading Short [{key}]…")
        _upload_file(service, short_path, meta["title"], meta["description"],
                     tags + ["shorts"], privacy, publish_at=meta["publish_at"])

    print(f"\n🎉 Day {day} posted to YouTube — 1 lesson + "
          f"{len(SHORTS_SCHEDULE_UTC)} Shorts spread across the day.")


def main():
    parser = argparse.ArgumentParser(description="Upload a finished lesson to YouTube")
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the metadata without uploading")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"],
                        default=None, help="override YT_PRIVACY (default: private)")
    args = parser.parse_args()
    upload_day(args.day, dry_run=args.dry_run, privacy=args.privacy)


if __name__ == "__main__":
    main()
