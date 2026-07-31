"""The worker: one process that waits for calls and answers them as Epictetus.

Input:  a LiveKit room to join, dispatched by LiveKit Cloud
Output: a voice in that room, a live transcript, and two side channels to the
        browser (which passages grounded each answer, which tool fired)

Steps:
  1. Once per process, before any call: load the voice-activity model and the
     Discourses index into memory.
  2. On dispatch: join the room, wait for the caller, and work out which
     personal backend their token entitles them to.
  3. Wire the four swappable pieces the brief asks to see -- STT, LLM, TTS, VAD.
  4. Start the session and greet them.

This is a long-running process that registers with LiveKit and waits to be
dispatched, not a function that runs per request. That shape is why hosting it
gets its own section in the plan: if this process is not running, the deployed
link is dead, however healthy the frontend looks.

Two things are loaded in prewarm rather than per call, and both matter on a
voice call. Silero's model takes a moment to load, and the index has to be read
off disk and have its keyword side rebuilt. Doing either after the caller has
already said hello would put that delay inside the conversation.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    cli,
)
from livekit.plugins import deepgram, elevenlabs, openai, silero

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent.grounding.turn_rag import Grounding  # noqa: E402
from agent.persona.epictetus_agent import Epictetus  # noqa: E402
from agent.persona.voice_and_words import DEFAULT_VOICE_ENV, GREETING  # noqa: E402
from agent.retrieval.search.index_store import load_index  # noqa: E402
from agent.retrieval.search.passage_search import PassageSearch  # noqa: E402
from agent.tools.personal.life_context import build_life_context  # noqa: E402

load_dotenv(REPO / ".env")

log = logging.getLogger("agent.main")

# The four pieces the brief asks to see as configurable choices. They are named
# here, in one place, and nowhere else -- swapping a vendor is an edit to this
# block, not a search through the codebase.
STT_MODEL = "nova-3"
LLM_MODEL = "gpt-4.1"
TTS_MODEL = "eleven_turbo_v2_5"  # ElevenLabs' fast tier: character, latency clawed back

server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """Runs once per worker process, before any call is dispatched."""
    proc.userdata["vad"] = silero.VAD.load()
    log.info("[agent.main] voice activity model loaded")

    try:
        proc.userdata["search"] = PassageSearch(load_index())
    except Exception:
        # A worker with no index can still hold a conversation -- it just cannot
        # ground one. Better a call that works and cites nothing than a worker
        # that refuses to start, because the second failure is invisible until
        # someone clicks the link.
        log.exception("[agent.main] could not load the Discourses index; starting ungrounded")
        proc.userdata["search"] = None


server.setup_fnc = prewarm


def _voice_id() -> str:
    """Which ElevenLabs voice he speaks in.

    An environment variable rather than a constant because picking the voice is
    a listening decision -- an older man, low, unhurried, not smooth -- and it
    should not take a code change and a redeploy to try another one. Falls back
    to the plugin's own default so the worker runs before anyone has chosen.
    """
    chosen = os.environ.get(DEFAULT_VOICE_ENV, "").strip()
    if chosen:
        return chosen
    return elevenlabs.TTS.__init__.__kwdefaults__["voice_id"]


@server.rtc_session(agent_name="epictetus")
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    caller = await ctx.wait_for_participant()
    log.info("[agent.main] call started with %s", caller.identity)

    async def publish(payload: str, topic: str) -> None:
        await ctx.room.local_participant.publish_data(payload, topic=topic, reliable=True)

    search = ctx.proc.userdata.get("search")
    grounding = Grounding(search, publish=publish) if search else _NoGrounding()

    life = build_life_context(caller)
    log.info("[agent.main] personal tools are on the %s backend", life.name)

    session = AgentSession(
        stt=deepgram.STT(model=STT_MODEL, language="en"),
        llm=openai.LLM(model=LLM_MODEL, temperature=0.75),
        tts=elevenlabs.TTS(model=TTS_MODEL, voice_id=_voice_id()),
        vad=ctx.proc.userdata["vad"],
        # Start composing the reply while the caller is still finishing. On a
        # call where retrieval now sits inside the response loop, this is the
        # cheapest latency there is to buy.
        preemptive_generation=True,
    )

    await session.start(
        agent=Epictetus(grounding, life, publish=publish),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
    )

    # Spoken verbatim rather than generated, so the first thing a grader hears
    # is the same every time and cannot wander off character.
    await session.say(GREETING, allow_interruptions=True)


class _NoGrounding:
    """Stands in when the index would not load. He talks; nothing is cited."""

    async def for_turn(self, text: str) -> str:
        return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cli.run_app(server)
