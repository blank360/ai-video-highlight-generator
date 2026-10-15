
import argparse
import csv
import json
import re
from pathlib import Path

WINDOW_SECONDS = 30
STEP_SECONDS = 5

HOOK_WORDS = {
    "why", "secret", "truth", "never", "impossible", "escape",
    "danger", "surprise", "suddenly", "kill", "stole", "caught",
    "mistake", "revenge", "finally", "discovered", "actually",
    "however", "instead", "love", "hate", "money", "police",
    "but", "because", "unless", "although", "really", "seriously",
    "promise", "wait", "sorry", "please", "guess", "realize",
    "betray", "wrong", "right", "dead", "secretly", "why"
}

REACTION_WORDS = {
    "what", "who", "where", "when", "how", "no", "yes",
    "wow", "oh", "damn", "wait", "really", "seriously",
    "unbelievable", "sorry", "please"
}


def load_scenes(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def load_transcript(path):
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        segments = data.get("segments", [])
    elif isinstance(data, list):
        segments = data
    else:
        segments = []

    if not isinstance(segments, list):
        raise ValueError("Transcript JSON must contain a segments list.")

    return segments


def parse_segments(transcript):
    """Normalize transcript timestamps and discard unusable segments."""
    valid = []

    for segment in transcript:
        try:
            start = float(segment["start"])
            end = float(segment["end"])
            text = str(segment.get("text", "")).strip()
        except (KeyError, TypeError, ValueError):
            continue

        # Very long segments often have poor timestamp alignment.
        if start < 0 or end <= start or end - start > 20 or not text:
            continue

        words = re.findall(r"\b[\w']+\b", text.lower())

        if not words:
            continue

        valid.append({
            "start": start,
            "end": end,
            "text": text,
            "words": words,
        })

    return sorted(valid, key=lambda item: item["start"])


def score_window(start, end, scenes, transcript):
    relevant = [
        seg for seg in transcript
        if seg["end"] > start and seg["start"] < end
    ]

    if not relevant:
        return None

    text = " ".join(seg["text"] for seg in relevant)
    words = re.findall(r"\b[\w']+\b", text.lower())
    word_count = len(words)

    if word_count < 20:
        return None

    duration = end - start
    speech_density = word_count / duration

    hook_count = sum(word in HOOK_WORDS for word in words)
    reaction_count = sum(word in REACTION_WORDS for word in words)

    questions = text.count("?")
    exclamations = text.count("!")

    # Dialogue activity: number of distinct transcript segments.
    segment_count = len(relevant)
    dialogue_activity = segment_count / duration

    # Scene changes add context, but are deliberately weighted lightly.
    scene_changes = sum(
        start < float(scene.get("start_seconds", 0)) < end
        for scene in scenes
    )

    # Reward reasonable speech density without making dense dialogue
    # automatically dominate all other signals.
    density_score = min(speech_density / 1.8, 1.0) * 10

    hook_score = min(hook_count, 6) * 1.0
    reaction_score = min(reaction_count, 5) * 0.8
    question_score = min(questions, 4) * 0.8
    exclamation_score = min(exclamations, 3) * 0.5
    activity_score = min(dialogue_activity * 8, 5)
    scene_score = min(scene_changes, 8) * 0.25

    # Penalize extremely sparse dialogue.
    sparse_penalty = 4 if speech_density < 0.5 else 0

    score = (
        density_score
        + hook_score
        + reaction_score
        + question_score
        + exclamation_score
        + activity_score
        + scene_score
        - sparse_penalty
    )

    return {
        "start_seconds": round(start, 2),
        "end_seconds": round(end, 2),
        "duration_seconds": round(duration, 2),
        "score": round(score, 2),
        "word_count": word_count,
        "scene_changes": scene_changes,
        "transcript_excerpt": text[:700].replace("\n", " "),
    }


def select_diverse(candidates, limit, minimum_gap):
    """Select high-scoring candidates distributed across the video."""
    if not candidates:
        return []

    candidates = sorted(
        candidates,
        key=lambda item: item["score"],
        reverse=True
    )

    selected = []

    for candidate in candidates:
        start = candidate["start_seconds"]
        end = candidate["end_seconds"]

        # Exclude windows that overlap or sit too close to a selected one.
        too_close = any(
            start < item["end_seconds"] + minimum_gap
            and end > item["start_seconds"] - minimum_gap
            for item in selected
        )

        if not too_close:
            selected.append(candidate)

        if len(selected) >= limit:
            break

    return sorted(selected, key=lambda item: item["score"], reverse=True)


def main():
    parser = argparse.ArgumentParser(
        description="Generate diverse dialogue-based highlight candidates."
    )
    parser.add_argument("--video", default="sample.mp4")
    parser.add_argument(
        "--limit",
        type=int,
        default=60,
        help="Maximum candidates to save (default: 60)."
    )
    parser.add_argument(
        "--window",
        type=float,
        default=WINDOW_SECONDS,
        help="Candidate window length in seconds (default: 30)."
    )
    parser.add_argument(
        "--step",
        type=float,
        default=STEP_SECONDS,
        help="Seconds between candidate starts (default: 5)."
    )
    parser.add_argument(
        "--minimum-gap",
        type=float,
        default=10,
        help="Minimum separation between selected windows (default: 10)."
    )
    args = parser.parse_args()

    if args.limit < 1 or args.window <= 0 or args.step <= 0:
        parser.error("--limit, --window, and --step must be positive.")

    video = Path(args.video).resolve()

    scene_file = video.with_name(f"{video.stem}_scenes.csv")
    transcript_file = video.with_name(
        f"{video.stem}_transcript.json"
    )

    if not video.is_file():
        raise FileNotFoundError(f"Video not found: {video}")

    if not scene_file.is_file() or not transcript_file.is_file():
        raise FileNotFoundError(
            "Required scene CSV or transcript JSON is missing.\n"
            f"Expected: {scene_file}\n"
            f"Expected: {transcript_file}"
        )

    print("Loading scene data and transcript...")
    scenes = load_scenes(scene_file)
    raw_transcript = load_transcript(transcript_file)
    transcript = parse_segments(raw_transcript)

    if not transcript:
        raise ValueError(
            "No usable transcript segments found after timestamp checks."
        )

    last_time = max(segment["end"] for segment in transcript)

    candidates = []
    start = 0.0

    print("Generating candidate windows...")

    while start + args.window <= last_time:
        result = score_window(
            start,
            start + args.window,
            scenes,
            transcript
        )

        if result is not None:
            candidates.append(result)

        start += args.step

    print(f"Scored {len(candidates)} candidate windows.")

    selected = select_diverse(
        candidates,
        args.limit,
        args.minimum_gap
    )

    output = video.with_name(f"{video.stem}_highlights.csv")

    fields = [
        "start_seconds",
        "end_seconds",
        "duration_seconds",
        "score",
        "word_count",
        "scene_changes",
        "transcript_excerpt",
    ]

    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)

    print(f"Selected {len(selected)} diverse candidates.")
    print(f"Saved: {output}\n")

    for index, item in enumerate(selected[:10], start=1):
        print(
            f"{index:02}. "
            f"{item['start_seconds']:.1f}s–"
            f"{item['end_seconds']:.1f}s | "
            f"heuristic score={item['score']:.1f}"
        )
        print(f"    {item['transcript_excerpt'][:180]}\n")


if __name__ == "__main__":
    main()
