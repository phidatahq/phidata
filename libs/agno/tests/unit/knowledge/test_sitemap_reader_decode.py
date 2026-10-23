"""Bounded decompression for SitemapReader._decode_sitemap_bytes (issue #11252)."""

import gzip

import pytest

from agno.knowledge.reader.sitemap_reader import SitemapReader


def sitemap_xml(fill: str = "x", count: int = 10) -> bytes:
    locs = "".join(f"<loc>https://a.test/{fill}{i}</loc>" for i in range(count))
    return f"<urlset>{locs}</urlset>".encode()


def test_plain_xml_passes_through():
    raw = sitemap_xml()
    assert SitemapReader._decode_sitemap_bytes(raw) == raw


def test_normal_gzip_sitemap_decodes():
    raw = gzip.compress(sitemap_xml())
    assert SitemapReader._decode_sitemap_bytes(raw) == sitemap_xml()


def test_corrupt_gzip_returns_raw():
    raw = b"\x1f\x8b" + b"not-really-gzip"
    assert SitemapReader._decode_sitemap_bytes(raw) == raw


def test_gzip_larger_than_limit_returns_raw_compressed():
    payload = gzip.compress(sitemap_xml(count=2000))
    decoded = SitemapReader._decode_sitemap_bytes(payload, max_bytes=64)
    assert decoded == payload


def test_gzip_exactly_at_limit_decodes():
    # Build an XML whose uncompressed size is exactly max_bytes.
    target = 256
    body = b"<urlset>" + b"a" * (target - len("<urlset></urlset>")) + b"</urlset>"
    assert len(body) == target
    raw = gzip.compress(body)
    assert SitemapReader._decode_sitemap_bytes(raw, max_bytes=target) == body


def test_isize_fast_path_rejects_before_decompressing():
    # A gzip stream whose trailer claims an uncompressed size over the limit is
    # rejected by the ISIZE pre-check without spending the decompression.
    payload = gzip.compress(sitemap_xml())
    lied = payload[:-4] + (64 * 1024 * 1024).to_bytes(4, "little")
    decoded = SitemapReader._decode_sitemap_bytes(lied, max_bytes=1024)
    assert decoded == lied
