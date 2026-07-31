from types import SimpleNamespace

import pytest

from agent.grounding.turn_filter.luna import LunaTurnFilter


class FakeResponses:
    def __init__(self, decision: bool):
        self.decision = decision
        self.calls: list[dict] = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=SimpleNamespace(retrieve=self.decision))


class FakeClient:
    def __init__(self, decision: bool):
        self.responses = FakeResponses(decision)


@pytest.mark.asyncio
async def test_luna_uses_one_small_structured_response():
    client = FakeClient(decision=False)
    turn_filter = LunaTurnFilter(client=client)

    decision = await turn_filter.should_retrieve(
        prior_assistant="Does the waiting feel less heavy now?",
        current_user="That helps. Okay. All right. Thanks.",
    )

    assert decision is False
    assert len(client.responses.calls) == 1
    request = client.responses.calls[0]
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "none"}
    assert request["store"] is False
    assert request["max_output_tokens"] <= 32
    assert request["timeout"] == 3.0
    assert "Does the waiting feel less heavy now?" in request["input"]
    assert "That helps. Okay. All right. Thanks." in request["input"]


@pytest.mark.asyncio
async def test_luna_keeps_a_substantive_decision_even_when_it_is_not_a_question():
    client = FakeClient(decision=True)
    turn_filter = LunaTurnFilter(client=client)

    decision = await turn_filter.should_retrieve(
        prior_assistant="Which choice is actually yours?",
        current_user="I think I will walk away.",
    )

    assert decision is True
