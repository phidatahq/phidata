"""PII masking must not corrupt non-string input_content."""

import pytest

from agno.exceptions import InputCheckError
from agno.guardrails.pii import PIIDetectionGuardrail
from agno.run.agent import RunInput


def test_mask_pii_rewrites_string_content_in_place():
    """String content is masked in place, preserving its exact type."""
    guardrail = PIIDetectionGuardrail(mask_pii=True)
    run_input = RunInput(input_content="contact me at a@b.com please")

    guardrail.check(run_input)

    assert isinstance(run_input.input_content, str)
    assert run_input.input_content == "contact me at ******* please"
    assert "a@b.com" not in run_input.input_content


def test_mask_pii_keeps_list_content_structure_intact():
    """Blocking a list-shaped input must leave input_content untouched, not flattened into a JSON string."""
    guardrail = PIIDetectionGuardrail(mask_pii=True)
    content = [{"type": "text", "text": "contact me at a@b.com please"}]
    run_input = RunInput(input_content=content)

    with pytest.raises(InputCheckError):
        guardrail.check(run_input)

    assert run_input.input_content == content
    assert isinstance(run_input.input_content, list)


def test_mask_pii_blocks_list_content_with_pii_detected():
    """When masking is impossible (non-string content), fail closed instead of passing PII through."""
    guardrail = PIIDetectionGuardrail(mask_pii=True)
    run_input = RunInput(input_content=[{"type": "text", "text": "contact me at a@b.com please"}])

    with pytest.raises(InputCheckError):
        guardrail.check(run_input)


def test_mask_pii_passes_clean_list_content_unchanged():
    """Non-string content without PII is not blocked and not rewritten."""
    guardrail = PIIDetectionGuardrail(mask_pii=True)
    content = [{"type": "text", "text": "no secrets here"}]
    run_input = RunInput(input_content=content)

    guardrail.check(run_input)

    assert run_input.input_content == content


async def test_mask_pii_blocks_list_content_async():
    """The async path blocks non-string content with PII detected."""
    guardrail = PIIDetectionGuardrail(mask_pii=True)
    run_input = RunInput(input_content=[{"type": "text", "text": "contact me at a@b.com please"}])

    with pytest.raises(InputCheckError):
        await guardrail.async_check(run_input)
