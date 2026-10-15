
import argparse
import csv
import json
import urllib.error
import urllib.request
from pathlib import Path


OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_ollama(prompt, model):
    """Send a prompt to the local Ollama model and parse its JSON response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    return json.loads(result["response"])


def load_transcript(path):
    """Load timestamped transcript segments from JSON."""
    with open(path, "r", encoding="utf-8") as file:
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


def get_dialogue(segments, start, end):
    """Collect transcript text overlapping a candidate clip."""
    lines = []

    for segment in segments:
        try:
            segment_start = float(segment.get("start", 0))
            segment_end = float(segment.get("end", 0))
        except (TypeError, ValueError):
            continue

        if segment_end >= start and segment_start <= end:
            text = str(segment.get("text", "")).strip()
            if text:
                lines.append(text)

    return " ".join(lines)


def clamp_score(value):
    """Convert a model score to an integer from 1 to 10."""
    try:
        return max(1, min(10, int(float(value))))
    except (TypeError, ValueError):
        return 1


def score_candidate(dialogue, duration, model):
    """Ask Qwen to evaluate the standalone-short potential."""
    prompt = f"""
You are an honest YouTube Shorts editor.

Evaluate this candidate using only the supplied dialogue.
Do not invent visual events or missing story context.

Duration: {duration:.1f} seconds
Dialogue:
{dialogue[:6000]}

Return a JSON object with exactly these fields:
{{
  "score": 1,
  "context": 1,
  "suspense": 1,
  "humor": 1,
  "emotion": 1,
  "payoff": 1,
  "reason": "Brief explanation"
}}

All six scores must be integers from 1 to 10.

score: overall potential as a standalone Short.
context: how understandable the moment is without extra context.
suspense: curiosity, tension, or anticipation.
humor: comedic potential.
emotion: emotional impact.
payoff: satisfying reveal, conclusion, or punchline.

Do not reward a clip simply for containing questions or dramatic words.
Lower the score when the dialogue lacks context or a clear payoff.
Be concise and honest.
"""

    result = ask_ollama(prompt, model)

    score_fields = [
        "score", "context", "suspense",
        "humor", "emotion", "payoff"
    ]

    scores = {
        field: clamp_score(result.get(field, 1))
        for field in score_fields
    }
    scores["reason"] = str(result.get("reason", "")).strip()

    return scores


def main():
    parser = argparse.ArgumentParser(
        description="Rank video highlights using local Qwen via Ollama."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Original video filename, e.g. sample.mp4"
    )
    parser.add_argument("--candidates", help="Optional candidate CSV path")
    parser.add_argument("--transcript", help="Optional transcript JSON path")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    video_path = Path(args.video).resolve()

    candidates_path = (
        Path(args.candidates).resolve()
        if args.candidates
        else video_path.parent / f"{video_path.stem}_highlights.csv"
    )

    transcript_path = (
        Path(args.transcript).resolve()
        if args.transcript
        else video_path.parent / f"{video_path.stem}_transcript.json"
    )

    output_path = video_path.parent / f"{video_path.stem}_ai_ranked.csv"

    for path in (video_path, candidates_path, transcript_path):
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

    if args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    print("Loading transcript...")
    segments = load_transcript(transcript_path)

    with open(
        candidates_path, "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        candidates = list(reader)
        original_fields = reader.fieldnames or []

    required_columns = {"start_seconds", "end_seconds"}

    if not required_columns.issubset(original_fields):
        raise ValueError(
            "The candidate CSV must contain start_seconds and end_seconds. "
            f"Found columns: {original_fields}"
        )

    if not candidates:
        raise ValueError("The candidate CSV contains no candidates.")

    candidates_to_score = candidates[:args.limit]
    ranked = []

    print(f"Found {len(candidates)} candidates.")
    print(f"Scoring up to {len(candidates_to_score)} candidates.")
    print(f"Model: {args.model}")
    print("Make sure Ollama is running.\n")

    for index, candidate in enumerate(candidates_to_score, start=1):
        try:
            start = float(candidate["start_seconds"])
            end = float(candidate["end_seconds"])
        except (TypeError, ValueError):
            print(f"[{index}] Skipping invalid timestamps.")
            continue

        if end <= start:
            print(f"[{index}] Skipping invalid clip duration.")
            continue

        dialogue = get_dialogue(segments, start, end)

        # Use the existing CSV excerpt if timestamp matching found no text.
        if not dialogue:
            dialogue = str(candidate.get("transcript_excerpt", "")).strip()

        candidate["ai_score"] = 0
        candidate["ai_context"] = 0
        candidate["ai_suspense"] = 0
        candidate["ai_humor"] = 0
        candidate["ai_emotion"] = 0
        candidate["ai_payoff"] = 0
        candidate["ai_reason"] = ""

        if not dialogue:
            candidate["ai_reason"] = "No transcript text found."
            ranked.append(candidate)
            print(f"[{index}/{len(candidates_to_score)}] No transcript text.")
            continue

        print(
            f"[{index}/{len(candidates_to_score)}] "
            f"Scoring {start:.1f}s–{end:.1f}s..."
        )

        try:
            scores = score_candidate(dialogue, end - start, args.model)

            candidate["ai_score"] = scores["score"]
            candidate["ai_context"] = scores["context"]
            candidate["ai_suspense"] = scores["suspense"]
            candidate["ai_humor"] = scores["humor"]
            candidate["ai_emotion"] = scores["emotion"]
            candidate["ai_payoff"] = scores["payoff"]
            candidate["ai_reason"] = scores["reason"]

            print(
                f"  Score: {scores['score']}/10 — "
                f"{scores['reason']}"
            )

        except urllib.error.URLError as error:
            raise RuntimeError(
                "Could not connect to Ollama at "
                f"{OLLAMA_URL}. Open the Ollama application "
                "and run the script again."
            ) from error
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            candidate["ai_reason"] = f"Could not parse model response: {error}"
            print(f"  Warning: {error}")

        ranked.append(candidate)

    # Put the highest AI scores first.
    ranked.sort(
        key=lambda row: int(row.get("ai_score", 0)),
        reverse=True
    )

    new_fields = [
        "ai_score",
        "ai_context",
        "ai_suspense",
        "ai_humor",
        "ai_emotion",
        "ai_payoff",
        "ai_reason"
    ]

    output_fields = list(original_fields)
    for field in new_fields:
        if field not in output_fields:
            output_fields.append(field)

    with open(
        output_path, "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=output_fields,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(ranked)

    print("\nAI ranking complete.")
    print(f"Output: {output_path}")
    print(f"Candidates written: {len(ranked)}")
    print("Your original CSV and other scripts were not modified.")


if __name__ == "__main__":
    main()
