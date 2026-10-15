
import json
import re
from pathlib import Path


def srt_time(seconds):
    milliseconds = round(max(0, seconds) * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)

    return (
        f"{hours:02}:{minutes:02}:{secs:02},"
        f"{milliseconds:03}"
    )


def split_caption(text, max_words=6):
    words = text.split()
    return [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
    ]


def create_srt(transcript_path, clip_start, clip_end, output_path):
    transcript_path = Path(transcript_path)

    with transcript_path.open(encoding="utf-8") as file:
        transcript = json.load(file)["segments"]

    cues = []

    for segment in transcript:
        start = float(segment["start"])
        end = float(segment["end"])

        # Ignore speech outside this clip.
        if end <= clip_start or start >= clip_end:
            continue

        start = max(start, clip_start)
        end = min(end, clip_end)

        # Convert source timestamps to clip-relative timestamps.
        local_start = start - clip_start
        local_end = end - clip_start

        text = re.sub(r"\s+", " ", segment["text"]).strip()
        if not text or local_end <= local_start:
            continue

        phrases = split_caption(text)
        duration = local_end - local_start
        total_words = sum(len(p.split()) for p in phrases)
        elapsed_words = 0

        for phrase in phrases:
            word_count = len(phrase.split())

            phrase_start = (
                local_start + duration * elapsed_words / total_words
            )
            elapsed_words += word_count
            phrase_end = (
                local_start + duration * elapsed_words / total_words
            )

            cues.append((phrase_start, phrase_end, phrase))

    cues.sort(key=lambda cue: cue[0])

    with open(output_path, "w", encoding="utf-8-sig") as file:
        for index, (start, end, text) in enumerate(cues, 1):
            file.write(
                f"{index}\n"
                f"{srt_time(start)} --> {srt_time(end)}\n"
                f"{text}\n\n"
            )

    print(f"Created {len(cues)} caption cues: {output_path}")
    return len(cues)
