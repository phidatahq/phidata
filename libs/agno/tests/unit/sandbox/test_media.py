import base64
import os

import pytest

from agno.exceptions import UnsupportedMediaError
from agno.media import Audio, File, Image
from agno.sandbox.media import MAX_MEDIA_BYTES, decode_media, encode_media, validate_media


def test_canonical_bytes_and_ids_ignore_ephemeral_media_ids():
    first = encode_media(
        {"files": [File(content=b"abc", filename="source.py")], "images": [Image(content=b"png", format="png")]}
    )
    second = encode_media(
        {"files": [File(content=b"abc", filename="source.py")], "images": [Image(content=b"png", format="png")]}
    )
    assert first == second
    decoded = decode_media(first)
    assert decoded["files"][0].content == b"abc"
    assert decoded["images"][0].content == b"png"
    assert decoded["files"][0].id == decode_media(second)["files"][0].id
    assert encode_media(decoded) == first


def test_explicit_sdk_file_read_never_forwards_host_path(tmp_path):
    path = tmp_path / "code.txt"
    path.write_bytes(b"code")
    with pytest.raises(ValueError, match="filesystem"):
        encode_media({"files": [File(filepath=path)]})
    wire = encode_media({"files": [File(filepath=path)]}, allow_local_paths=True)
    assert wire[0]["name"] == "code.txt" and wire[0]["content"] == base64.b64encode(b"code").decode()
    assert str(tmp_path) not in str(wire)
    link = tmp_path / "link.txt"
    link.symlink_to(path)
    with pytest.raises(OSError):
        encode_media({"files": [File(filepath=link)]}, allow_local_paths=True)
    fifo = tmp_path / "fifo.txt"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular"):
        encode_media({"files": [File(filepath=fifo)]}, allow_local_paths=True)


@pytest.mark.parametrize("field", ["filepath", "url", "media_reference", "external"])
def test_json_cannot_request_service_paths_or_remote_fetch(field):
    with pytest.raises(ValueError, match="paths or remote"):
        encode_media({"files": [{"content": "YQ==", field: "/secret"}]})


def test_json_base64_and_limits():
    assert (
        decode_media(encode_media({"files": [{"content": "YWJj", "filename": "a.txt"}]}))["files"][0].content == b"abc"
    )
    with pytest.raises(ValueError, match="512 KiB"):
        encode_media({"files": [File(content=b"a" * MAX_MEDIA_BYTES), File(content=b"b")]})
    with pytest.raises(ValueError, match="16"):
        encode_media({"files": [File(content=b"a")] * 17})
    with pytest.raises(ValueError, match="base64"):
        encode_media({"files": [{"content": "not base64!"}]})
    with pytest.raises(UnsupportedMediaError):
        encode_media({"audio": [Audio(content=b"audio")]})


@pytest.mark.parametrize(
    "patch",
    [{"name": "../bad"}, {"name": "a/b"}, {"name": "a\\b"}, {"kind": "audio"}, {"content": "YR=="}, {"extra": True}],
)
def test_runtime_validates_wire_not_just_service(patch):
    wire = {"kind": "file", "name": "a.txt", "content": "YQ=="}
    with pytest.raises(ValueError):
        validate_media([{**wire, **patch}])
