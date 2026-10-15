
import argparse
import csv
import subprocess
from pathlib import Path

from caption_utils import create_srt


def export_shorts(video_path, csv_path, transcript_path, limit=5):
    video = Path(video_path).resolve()
    candidates_file = Path(csv_path).resolve()
    transcript_file = Path(transcript_path).resolve()

    for path in (video, candidates_file, transcript_file):
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

    output_dir = video.parent / "output_shorts"
    output_dir.mkdir(parents=True, exist_ok=True)

    with candidates_file.open(
        newline="", encoding="utf-8-sig"
    ) as file:
        candidates = list(csv.DictReader(file))[:limit]

    if not candidates:
        raise RuntimeError("No highlight candidates found.")

    for index, candidate in enumerate(candidates, start=1):
        start = float(candidate["start_seconds"])
        end = float(candidate["end_seconds"])
        duration = end - start

        if start < 0 or duration <= 0:
            print(f"Skipping invalid candidate {index}")
            continue

        output = output_dir / f"short_{index:02}.mp4"
        subtitle = output_dir / f"short_{index:02}.srt"

        create_srt(
            transcript_path=str(transcript_file),
            clip_start=start,
            clip_end=end,
            output_path=str(subtitle),
        )

        print(
            f"\nExporting clip {index}/{len(candidates)}: "
            f"{start:.1f}s - {end:.1f}s"
        )

        # Escape the subtitle path for FFmpeg's filter syntax.
        subtitle_filter_path = str(subtitle).replace("\\", "/")
        subtitle_filter_path = subtitle_filter_path.replace(":", r"\:")
        subtitle_filter_path = subtitle_filter_path.replace("'", r"\'")

        video_filter = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:10[bgblur];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgsmall];"
            "[bgblur][fgsmall]overlay=(W-w)/2:(H-h)/2,"
            "setsar=1,format=yuv420p,"
            f"subtitles='{subtitle_filter_path}':"
            
"force_style='FontName=Arial,FontSize=14,"
"Bold=1,PrimaryColour=&H00FFFFFF,"
"OutlineColour=&H00000000,Outline=2,Shadow=0,"
"Alignment=2,MarginV=240,WrapStyle=2'"

        )

        command = [
            "ffmpeg", "-hide_banner", "-y",
            "-ss", str(start),
            "-i", str(video),
            "-t", str(duration),
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-vf", video_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output),
        ]

        result = subprocess.run(command, check=False)

        if result.returncode == 0 and output.exists():
            print(f"Saved video: {output}")
            print(f"Saved subtitles: {subtitle}")
        else:
            print(
                f"Export failed for clip {index}. "
                "Review the FFmpeg error above."
            )

    print(f"\nFinished. Check: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export vertical Shorts with burned-in captions."
    )
    parser.add_argument("--video", default="sample.mp4")
    parser.add_argument("--csv", default="sample_highlights.csv")
    parser.add_argument(
        "--transcript", default="sample_transcript.json"
    )
    parser.add_argument("--limit", type=int, default=2)

    args = parser.parse_args()

    export_shorts(
        args.video,
        args.csv,
        args.transcript,
        args.limit,
    )
