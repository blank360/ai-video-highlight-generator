
from caption_utils import create_srt

create_srt(
    transcript_path="sample_transcript.json",
    clip_start=45,
    clip_end=90,
    output_path="test_captions.srt",
)
