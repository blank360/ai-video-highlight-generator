
import argparse
import csv
from pathlib import Path

import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


def detect_scenes(video_path: str, threshold: float = 27.0):
    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    # Read video metadata.
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("Could not open video. Check its format.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if fps <= 0 or frame_count <= 0:
        raise RuntimeError("Invalid video metadata.")

    duration = frame_count / fps

    print(f"\nVideo: {path.name}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.2f}")
    print(f"Duration: {duration:.2f} seconds")
    print("\nDetecting scene changes...")

    # Detect abrupt visual changes.
    video = open_video(str(path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video, show_progress=True)

    scenes = manager.get_scene_list()

    # Convert scenes to timestamped records.
    records = []
    for index, (start, end) in enumerate(scenes, start=1):
        start_sec = start.get_seconds()
        end_sec = end.get_seconds()

        records.append({
            "scene": index,
            "start_seconds": round(start_sec, 3),
            "end_seconds": round(end_sec, 3),
            "duration_seconds": round(end_sec - start_sec, 3),
        })

    # Save results next to the source video.
    output_path = path.with_name(f"{path.stem}_scenes.csv")

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scene",
                "start_seconds",
                "end_seconds",
                "duration_seconds",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"\nDetected {len(records)} scenes.")
    print(f"Results saved to: {output_path}")

    for record in records[:15]:
        print(
            f"Scene {record['scene']:>3}: "
            f"{record['start_seconds']:>8.2f}s - "
            f"{record['end_seconds']:>8.2f}s "
            f"({record['duration_seconds']:.2f}s)"
        )

    if len(records) > 15:
        print(f"...and {len(records) - 15} more scenes.")

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect scene boundaries in a video."
    )
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=27.0,
        help="Scene-change sensitivity; lower values detect more changes",
    )

    args = parser.parse_args()
    detect_scenes(args.video, args.threshold)
