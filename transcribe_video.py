
import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel


def transcribe_video(video_path: str, model_size: str = "base"):
    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    print(f"Loading Whisper model: {model_size}")
    print("The first run may download the model files.")

    # CPU-friendly initial configuration.
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
    )

    print(f"\nTranscribing: {path.name}")

    segments, info = model.transcribe(
        str(path),
        beam_size=5,
        vad_filter=True,
    )

    results = []
    for segment in segments:
        item = {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        }
        results.append(item)

        print(
            f"[{item['start']:8.2f}s - "
            f"{item['end']:8.2f}s] {item['text']}"
        )

    output_path = path.with_name(f"{path.stem}_transcript.json")

    output = {
        "video": path.name,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "segments": results,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"\nDetected language: {info.language}")
    print(f"Transcribed segments: {len(results)}")
    print(f"Saved transcript: {output_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe a video with timestamped dialogue."
    )
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium"],
        default="base",
        help="Whisper model size; base is a reasonable starting point",
    )

    args = parser.parse_args()
    transcribe_video(args.video, args.model)
