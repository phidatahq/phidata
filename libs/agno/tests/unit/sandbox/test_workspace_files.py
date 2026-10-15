import os

import pytest

from agno.sandbox.files import _outputs, _prepare, validate_files


def test_snapshot_is_materialized_and_can_be_replayed(tmp_path):
    files = {"product/brief.md": "  Keep docs current\n"}
    _prepare(files, tmp_path)
    assert (tmp_path / "context/product/brief.md").read_text() == files["product/brief.md"]
    (tmp_path / "output/report.md").write_text("Checks passed")
    _prepare(files, tmp_path)
    assert _outputs(tmp_path) == {"report.md": "Checks passed"}


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "a/../b", "a//b", "a\\b", "a/./b"])
def test_input_rejects_escaping_or_ambiguous_paths(path):
    with pytest.raises(ValueError):
        validate_files({path: "text"})


def test_output_rejects_symlinks_hardlinks_binary_and_oversize(tmp_path):
    _prepare({}, tmp_path)
    external = tmp_path / "secret"
    external.write_text("secret")
    link = tmp_path / "output/link"
    link.symlink_to(external)
    with pytest.raises(OSError):
        _outputs(tmp_path)
    link.unlink()
    os.link(external, link)
    with pytest.raises(ValueError):
        _outputs(tmp_path)
    link.unlink()
    link.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        _outputs(tmp_path)
    link.write_text("x" * 250001)
    with pytest.raises(ValueError):
        _outputs(tmp_path)


def test_input_size_and_directory_symlink_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        validate_files({"large": "é" * 125001})
    (tmp_path / "context").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        _prepare({}, tmp_path)


def test_both_adapters_forward_workspace_files():
    from agno.agents.claude import ClaudeAgent
    from agno.agents.codex import CodexAgent
    from agno.sandbox._harness import submission
    from agno.sandbox.docker import DockerSandbox

    provider = DockerSandbox(image="fixture")
    codex = CodexAgent(id="codex", sandbox=provider)
    claude = ClaudeAgent(id="claude", sandbox=provider)
    expected = {"product/brief.md": "Keep docs current"}
    for agent in (codex, claude):
        assert submission(agent, "Update docs", {"workspace_files": expected})["config"]["_workspace_files"] == expected
