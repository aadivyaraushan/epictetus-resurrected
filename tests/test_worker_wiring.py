"""The four pieces must build from the environment variables we document.

This exists because of a real outage. The ElevenLabs plugin reads its key from
ELEVEN_API_KEY. Our .env, our .env.example, our README and our container all say
ELEVENLABS_API_KEY. Nothing connected the two, so the key was present and unused,
and the very first real call died 0.16 seconds after the caller arrived:

    ValueError: ElevenLabs API key is required, either as argument or set
    ELEVEN_API_KEY environmental variable

Nothing caught it earlier, and it is worth being precise about why. The voice
round-trip test called the ElevenLabs REST API directly with the key in a header,
so it proved the key was good while saying nothing about whether the plugin could
find it. The persona test used only the language model. Every layer was exercised
except the one line that hands the key to the plugin.

So these tests build the real objects from a stripped environment. They make no
network calls -- a constructor that raises on a missing key raises before any
request is made, which is exactly the failure being guarded.
"""

from __future__ import annotations

import pytest

from agent.main import build_llm, build_stt, build_tts


@pytest.fixture
def clean_env(monkeypatch):
    """Only the variables we actually document, and none of the plugins' own."""
    for stray in ("ELEVEN_API_KEY", "OPENAI_API_KEY", "DEEPGRAM_API_KEY"):
        monkeypatch.delenv(stray, raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    return monkeypatch


def test_tts_builds_from_the_variable_we_document(clean_env):
    """The regression itself: ELEVENLABS_API_KEY set, ELEVEN_API_KEY absent."""
    assert build_tts() is not None


def test_tts_uses_the_chosen_voice(clean_env):
    clean_env.setenv("ELEVENLABS_VOICE_ID", "some-chosen-voice")
    assert build_tts()._opts.voice_id == "some-chosen-voice"


def test_tts_falls_back_to_a_default_voice(clean_env):
    """The worker has to run before anyone has picked a voice."""
    assert build_tts()._opts.voice_id


def test_tts_says_which_variable_is_missing(clean_env):
    """A worker that dies on a missing key should name the key we document,
    not the plugin's own name -- otherwise the message sends you looking for a
    variable that appears nowhere in this repo."""
    clean_env.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        build_tts()


def test_stt_builds_from_the_variable_we_document(clean_env):
    assert build_stt() is not None


def test_stt_says_which_variable_is_missing(clean_env):
    clean_env.delenv("DEEPGRAM_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        build_stt()


def test_llm_builds_from_the_variable_we_document(clean_env):
    assert build_llm() is not None


def test_llm_uses_luna_without_reasoning_for_voice_tools(clean_env):
    """Chat Completions tools require effective reasoning ``none`` on GPT-5.6.

    Luna keeps this spoken path in the family's low-latency, low-cost role; the
    explicit reasoning setting keeps both function tools available.
    """
    llm = build_llm()

    assert llm._opts.model == "gpt-5.6-luna"
    assert llm._opts.reasoning_effort == "none"


def test_llm_says_which_variable_is_missing(clean_env):
    clean_env.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_llm()
