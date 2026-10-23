"""Review an existing Step 6 export; never render or publish a production lesson."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/phase4-export-review"
PACKAGE = BASE / "package"
EVIDENCE = PACKAGE / "build/phase4-demo/evidence"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected is not None and urllib.parse.urlparse(new_url).hostname != "api.github.com":
            redirected.remove_header("Authorization")
        return redirected


def api(path: str) -> bytes:
    request = urllib.request.Request(
        "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"] + path,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json"})
    with urllib.request.build_opener(ArtifactRedirect()).open(request, timeout=120) as response:
        return response.read()


def download() -> None:
    run_id = int(os.environ["DEMO_RUN_ID"])
    for attempt in range(180):
        run = json.loads(api(f"/actions/runs/{run_id}"))
        if run["status"] == "completed":
            if run["conclusion"] != "success":
                raise ValueError("The selected demo did not pass its complete workflow")
            break
        print(f"Waiting for demo run {run_id}: {run['status']}", flush=True)
        time.sleep(15)
    else:
        raise TimeoutError("The selected demo has not completed within 45 minutes")
    artifacts = json.loads(api(f"/actions/runs/{run_id}/artifacts"))["artifacts"]
    artifact = next(item for item in artifacts if item["name"] == "phase4-step6-real-hybrid-lesson")
    data = api(f"/actions/artifacts/{artifact['id']}/zip")
    expected = artifact.get("digest")
    if expected and "sha256:" + hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Artifact ZIP digest mismatch")
    PACKAGE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            target = (PACKAGE / member.filename).resolve()
            if not target.is_relative_to(PACKAGE.resolve()):
                raise ValueError("Unsafe artifact path")
        archive.extractall(PACKAGE)
    (EVIDENCE / "review-source.json").write_text(json.dumps({
        "runId": run_id, "headSha": run["head_sha"], "artifactId": artifact["id"],
        "archiveSha256": hashlib.sha256(data).hexdigest()}, indent=2) + "\n")


def samples(path: Path, seconds: float, channel: str | None = None):
    import numpy as np

    command = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(seconds),
               "-i", str(path), "-t", "2", "-vn"]
    if channel is not None:
        command += ["-af", "pan=mono|c0=" + channel]
    command += ["-ac", "1", "-ar", "8000", "-f", "f32le", "pipe:1"]
    return np.frombuffer(subprocess.check_output(command), dtype="<f4")


def review() -> None:
    import numpy as np
    from PIL import Image

    report = json.loads((EVIDENCE / "final-render-verification.json").read_text())
    protection = json.loads((EVIDENCE / "production-unchanged.json").read_text())
    provenance = json.loads((EVIDENCE / "source-provenance.json").read_text())
    if not report["passed"] or len(report["chapters"]) != 9 or not protection["passed"]:
        raise ValueError("Missing complete final verification or production protection")
    for field, relative in (("cell1", "pipeline/cell1_lesson.py"),
                            ("cell4", "pipeline/cell4_animation.py")):
        if digest(ROOT / relative) != provenance[field]:
            raise ValueError("Export renderer does not match checked-out source: " + relative)
    full = PACKAGE / "remotion/build/phase4-demo/Phase4_Complete_Hybrid_Lesson.mp4"
    short = full.with_name("Phase4_Formula_Short.mp4")
    for key, path in (("full", full), ("short", short)):
        if digest(path) != report[key]["sha256"]:
            raise ValueError("Final MP4 digest differs from the successful CI report")
    props = json.loads(full.with_name("short.json").read_text())
    formula = next(item for item in props["chapters"] if item["id"] == "scene-05")
    source = PACKAGE / "build/phase4-demo/output/audio/lesson_999/scene_05.mp3"
    windows = []
    for seconds in (0.5, formula["durationInFrames"] / 60):
        original = samples(source, seconds)
        left = samples(short, props["introFrames"] / 30 + seconds, "FL")
        right = samples(short, props["introFrames"] / 30 + seconds, "FR")
        if len(left) != len(right) or not np.allclose(left, right, rtol=0, atol=.005):
            raise ValueError("Short left/right narration differs")
        length = min(len(original), len(left)) - 320
        reference = original[160:160 + length]
        if length < 1000 or float(np.sqrt(np.mean(reference ** 2))) < 1e-6:
            raise ValueError("Short verification window has insufficient speech")
        correlations, gains = [], []
        for offset in range(0, 321, 8):
            candidate = left[offset:offset + length]
            correlations.append(float(np.corrcoef(reference, candidate)[0, 1]))
            gains.append(float(np.sqrt(np.mean(candidate ** 2)) / np.sqrt(np.mean(reference ** 2))))
        best = int(np.nanargmax(correlations))
        if correlations[best] < .92 or not .75 < gains[best] < 1.25:
            raise ValueError("Short narration alignment or gain failed")
        windows.append({"sourceSeconds": seconds, "correlation": correlations[best], "gain": gains[best]})
    sheet = Image.new("RGB", (1440, 810), "#081b33")
    for index, chapter in enumerate(report["chapters"]):
        with Image.open(EVIDENCE / chapter["reviewFrame"]) as image:
            sheet.paste(image.resize((480, 270)), ((index % 3) * 480, (index // 3) * 270))
    sheet.save(EVIDENCE / "all-nine-chapters.png")
    concept = next(chapter for chapter in report["chapters"] if chapter["step"] == "concept")
    transition = EVIDENCE / "concept-transition-review.png"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss",
                    str(concept["startSeconds"] + concept["durationSeconds"] * .55),
                    "-i", str(full), "-frames:v", "1", str(transition)], check=True)
    result = {"passed": True, "shortSpeechWindows": windows,
              "rendererSourceMatches": True, "downloadedMediaHashesMatch": True}
    (EVIDENCE / "independent-export-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    for name in ("all-nine-chapters.png", "concept-transition-review.png", "short-phone-360.png"):
        encoded = base64.b64encode((EVIDENCE / name).read_bytes()).decode("ascii")
        for offset in range(0, len(encoded), 16000):
            print("MCME_IMAGE_CHUNK::" + name + "::" + str(offset) + "::" + encoded[offset:offset + 16000], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["download", "review"])
    globals()[parser.parse_args().command]()
