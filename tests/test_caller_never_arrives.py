"""A caller who changes their mind is not an error.

Seen in the live worker log: someone clicked Start Call, then denied the
microphone prompt or closed the tab. The room emptied, and the agent -- still
waiting for them -- died with an unhandled exception and a full traceback:

    RuntimeError: room disconnected while waiting for participant

Nothing was broken. Somebody just left. But it is logged identically to a real
fault, which is exactly the noise that hides a real fault later, on a deployed
worker whose logs nobody is watching closely.
"""

from __future__ import annotations

import pytest

from agent.main import entrypoint


class _FakeProc:
    def __init__(self):
        self.userdata = {"vad": object(), "search": None}


class _FakeCtx:
    """Only the surface entrypoint touches before it gives up waiting."""

    def __init__(self, failure: Exception):
        self.proc = _FakeProc()
        self._failure = failure
        self.connected = False

    async def connect(self):
        self.connected = True

    async def wait_for_participant(self):
        raise self._failure


@pytest.mark.asyncio
async def test_a_caller_who_never_arrives_ends_the_job_quietly():
    ctx = _FakeCtx(RuntimeError("room disconnected while waiting for participant"))

    await entrypoint(ctx)  # must not raise

    assert ctx.connected


@pytest.mark.asyncio
async def test_a_real_fault_still_surfaces():
    """Swallowing every exception here would hide genuine breakage behind the
    same silence, so only the disconnect is treated as ordinary."""
    ctx = _FakeCtx(ValueError("the ElevenLabs key is missing"))

    with pytest.raises(ValueError):
        await entrypoint(ctx)
