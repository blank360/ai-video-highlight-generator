# AI Video Highlight Generator 🎬

An AI-assisted video processing pipeline that analyzes long-form videos, identifies potential highlights, ranks candidate clips using a locally running LLM, and exports vertical YouTube Shorts with captions.

The project combines speech transcription, scene detection, heuristic-based candidate selection, local AI ranking, and FFmpeg-based video rendering.

## ✨ Features

- **Scene Detection:** Detect scene changes using PySceneDetect.
- **Speech Transcription:** Transcribe video audio locally using Faster-Whisper.
- **Highlight Detection:** Generate candidate clips using dialogue cues, speech density, and scene changes.
- **AI-Powered Ranking:** Evaluate candidates with Qwen 2.5 3B through Ollama.
- **Vertical Video Export:** Convert selected clips into a 9:16 format.
- **Automatic Captions:** Generate and burn subtitles into exported videos.
- **Local Processing:** Run transcription and AI ranking locally without requiring a paid AI API.

## 🛠️ Tech Stack

- Python
- FFmpeg
- OpenCV
- PySceneDetect
- Faster-Whisper
- Ollama
- Qwen 2.5 3B
- CSV and JSON for intermediate data

## ⚙️ Prerequisites

Install the following before running the project:

- Python 3.11 or a compatible Python version
- FFmpeg
- Ollama
- Qwen 2.5 3B model

Useful links:

- [Python](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html)
- [Ollama](https://ollama.com/download)

Download the model:

```bash
ollama pull qwen2.5:3b
```

## 🚀 Installation

Clone the repository:

```bash
git clone <YOUR_REPOSITORY_URL>
cd videoG
```

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
python -m pip install opencv-python scenedetect faster-whisper
```

Make sure FFmpeg is available:

```bash
ffmpeg -version
```

Start Ollama if it is not already running.

## 📂 Project Structure

```text
videoG/
├── scene_detector.py
├── transcribe_video.py
├── find_highlights.py
├── ai_rank_highlights.py
├── export_shorts.py
├── caption_utils.py
├── test_captions.py
├── sample.mp4
├── sample_scenes.csv
├── sample_transcript.json
├── sample_highlights.csv
├── sample_ai_ranked.csv
└── output_shorts/
```

Generated media and sample data are examples of runtime outputs, not required source files. Your repository may contain additional files.

## ▶️ Usage

Place your input video in the project directory.

### 1. Detect scenes

```bash
python scene_detector.py sample.mp4
```

This generates a scene CSV containing detected scene boundaries.

### 2. Transcribe the video

```bash
python transcribe_video.py --model base sample.mp4
```

The transcription stage generates timestamped transcript data.

### 3. Generate highlight candidates

```bash
python find_highlights.py --video sample.mp4 --limit 60
```

This generates candidate windows based on dialogue and scene-related signals.

### 4. Rank candidates using AI

```bash
python ai_rank_highlights.py --video sample.mp4 --limit 60
```

The local Qwen model evaluates candidate dialogue and assigns scores for overall potential, context, suspense, humor, emotion, and payoff.

### 5. Export Shorts

Check the supported arguments first:

```bash
python export_shorts.py --help
```

Use the arguments shown by your installed version to export the selected candidates. The exporter generates vertical videos with captions in the `output_shorts` directory.

## 🧠 How It Works

1. The input video is analyzed for scene changes.
2. Audio is transcribed into timestamped dialogue.
3. Candidate time windows are generated using heuristic scoring.
4. Ollama runs Qwen locally to assess candidate dialogue.
5. Candidates are ranked using their AI scores.
6. FFmpeg renders selected clips in vertical format with subtitles.

## ⚠️ Current Limitations

- Highlight selection and AI ranking are experimental.
- Transcript-based ranking cannot reliably understand visual comedy, facial expressions, or visual reveals.
- AI scores do not guarantee engagement or virality.
- Hindi and other language performance depends on transcription quality and the language capabilities of the selected model.
- Long videos can require substantial processing time and disk space.
- Full end-to-end automation and a graphical interface are not yet complete.

## 🔒 Privacy

Transcription and AI ranking are designed to run locally. Initial installation and model downloads require an internet connection.

## 🗺️ Roadmap

- Improve contextual highlight detection.
- Improve multilingual transcription and ranking.
- Integrate the complete workflow into a single command.
- Build a simple video upload interface.
- Add batch processing and resumable jobs.
- Improve caption timing and visual composition.
- Add automated testing and error recovery.

