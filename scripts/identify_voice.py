#!/usr/bin/env python3
"""Standalone script to analyze an audio file and identify/enroll the speaker's voice using local database."""

import sys
import asyncio
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transcribe.application.container import ServiceContainer
from transcribe.domain.entities import TranscriptSegment


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/identify_voice.py <audio_file_path> [optional_speaker_name]")
        sys.exit(1)

    audio_path = Path(sys.argv[1]).resolve()
    if not audio_path.is_file():
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)

    custom_name = sys.argv[2].strip() if len(sys.argv) > 2 else None

    container = ServiceContainer()
    speaker_id_engine = container.get_speaker_identifier()
    dummy_seg = TranscriptSegment(meeting_id="sample", start=0.0, end=10.0, text="Voice Sample", speaker_id="SAMPLE")

    print(f"\n🎙️ Analyzing audio voice sample: {audio_path.name}...")
    matched_name = asyncio.run(speaker_id_engine.identify(dummy_seg, audio_path))
    embedding = speaker_id_engine._extract_voice_embedding(dummy_seg, audio_path)
    match_speaker, score = container.speaker_db.match_voice_embedding(embedding)

    print("=" * 60)
    print(f"File Path:          {audio_path}")
    print(f"Identified Speaker: {matched_name}")

    if match_speaker:
        print(f"Match Status:       MATCHED (Confidence: {score * 100:.1f}%)")
        print(f"Profile ID:         {match_speaker.id}")
        print(f"Known Aliases:      {', '.join(match_speaker.aliases) if match_speaker.aliases else 'None'}")
        print("=" * 60)
        print(f"✅ Voice recognized as saved speaker: '{match_speaker.name}'\n")
    else:
        print(f"Match Status:       NEW / UNENROLLED VOICE")
        print("=" * 60)
        if custom_name:
            # Look up newly created profile or assign name
            spk = container.speaker_db.find_by_name(matched_name)
            if spk:
                container.speaker_db.update_speaker_details(spk.id, name=custom_name)
            print(f"👤 Successfully enrolled new voice as: '{custom_name}'\n")
        else:
            print(f"ℹ️ Enrolled as temporary profile: '{matched_name}'")
            print(f"   To rename later, run: transcribe speaker-rename '{matched_name}' 'Real Name'\n")

if __name__ == "__main__":
    main()
