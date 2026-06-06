from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BargeInConfig:
    """Tuning knobs for barge-in (caller interruption) behaviour.

    Passed to VoiceAssistant at construction time.  Adjust thresholds in
    backend/.env — these are the defaults that work for clean-room demos.
    """

    # Seconds of continuous caller speech required before we interrupt TTS.
    # Lower → more responsive; higher → fewer false triggers on filler words.
    interrupt_speech_duration: float = 0.5

    # Minimum words the STT must detect before treating the utterance as
    # a genuine barge-in (filters single-word noise like "um", "uh").
    interrupt_min_words: int = 1

    # Allow interruptions from the caller at all.
    allow_interruptions: bool = True


# Singleton used by the pipeline — override in tests if needed.
DEFAULT_BARGE_IN = BargeInConfig()
