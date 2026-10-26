import json
from uuid import uuid4

import httpx
import pytest
from mcp import Client

from reel_studio_mcp.schemas import Document
from reel_studio_mcp.server import build_server

BASE = "https://studio.test/api/v1"
TOKEN = "private-staff-token"
PROJECT = str(uuid4())


def connector(handler, media_root=None):
    return build_server(BASE, TOKEN, str(media_root) if media_root else None,
                        transport=httpx.MockTransport(handler))


def content(result):
    return " ".join(block.text for block in result.content if hasattr(block, "text"))


async def test_discovery_resources_and_safe_update_contract():
    server = connector(lambda _: pytest.fail("Help must not call the API"))
    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert "delete_project" not in tools
        assert set(tools["update_project"].input_schema["required"]) == {
            "project_id", "revision", "title", "track_id", "is_template", "document",
        }
        assert tools["get_project"].annotations.read_only_hint
        assert tools["update_project"].annotations.destructive_hint
        schema = json.loads((await client.read_resource("studio://schema")).contents[0].text)
        assert schema["Document"] == Document.model_json_schema()
        help_result = await client.call_tool("studio_help", {})
        assert not help_result.is_error
        assert "preview first" in content(help_result)
        assert "local_uploads_enabled" in content(help_result)


async def test_bounded_search_and_validation_before_api():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert request.url.path == "/api/v1/reels/tracks"
        return httpx.Response(200, json=[{"id": str(i), "title": "Song", "artist": "Ali"} for i in range(120)])

    async with Client(connector(handler)) as client:
        result = await client.call_tool("list_tracks", {"query": "ali", "offset": 10, "limit": 5})
        assert not result.is_error
        assert len(json.loads(content(result))["items"]) == 5
        assert json.loads(content(result))["total"] == 120
        for name, args in (
            ("list_tracks", {"limit": 101}), ("list_projects", {"offset": -1}),
            ("get_project", {"project_id": "../uploads"}),
            ("create_project", {"data": {"title": "Bad", "document": {"clip_end": 181}}}),
            ("create_project", {"data": {"title": "Bad", "document": {"unknown": True}}}),
        ):
            assert (await client.call_tool(name, args)).is_error
    assert len(requests) == 1


async def test_update_preserves_document_and_render_defaults_to_preview():
    payloads = []

    def handler(request):
        body = json.loads(request.content)
        payloads.append((request.method, str(request.url), body))
        return httpx.Response(200, json={"id": PROJECT, "revision": 8})

    document = Document(layers=[{"id": "title", "kind": "text", "text": "Keep me", "locked": True}]).model_dump(mode="json")
    async with Client(connector(handler)) as client:
        result = await client.call_tool("update_project", {
            "project_id": PROJECT, "revision": 7, "title": "Changed title",
            "track_id": None, "is_template": True, "document": document,
        })
        assert not result.is_error
        result = await client.call_tool("render_project", {
            "project_id": PROJECT, "data": {"revision": 8, "request_id": str(uuid4())},
        })
        assert not result.is_error
    assert payloads[0][0] == "PATCH"
    assert payloads[0][2]["document"] == document
    assert payloads[0][2]["is_template"] is True
    assert payloads[1][2]["preview"] is True
    assert payloads[1][2]["preview_start"] == 0


async def test_project_discovery_returns_summaries():
    def handler(request):
        assert request.url.params["offset"] == "20"
        assert request.url.params["limit"] == "10"
        return httpx.Response(200, json=[{"id": PROJECT, "title": "Song", "revision": 3,
                                        "document": {"layers": []}, "assets": []}])

    async with Client(connector(handler)) as client:
        result = await client.call_tool("list_projects", {"offset": 20, "limit": 10})
    assert not result.is_error
    assert "document" not in content(result) and "assets" not in content(result)
    assert PROJECT in content(result)


@pytest.mark.parametrize("status,detail,expected", [
    (401, TOKEN, "expired or invalid"), (403, TOKEN, "permission"),
    (409, "reel_revision_conflict", "reconcile"),
    (422, [{"input": TOKEN}], "Invalid Studio input"),
    (500, "https://storage.test/?signature=secret", "service availability"),
    (302, TOKEN, "request failed"),
])
async def test_api_errors_are_safe(status, detail, expected, caplog):
    async with Client(connector(lambda _: httpx.Response(status, json={"detail": detail}))) as client:
        result = await client.call_tool("get_project", {"project_id": PROJECT})
    assert result.is_error
    assert expected in content(result)
    assert TOKEN not in content(result) + caplog.text
    assert "signature=secret" not in content(result) + caplog.text


async def test_network_and_stored_job_errors_are_safe():
    def handler(request):
        raise httpx.ConnectError(f"{TOKEN} https://storage.test/?signature=secret", request=request)

    async with Client(connector(handler)) as client:
        result = await client.call_tool("get_project", {"project_id": PROJECT})
        assert result.is_error and TOKEN not in content(result)
    async with Client(connector(lambda _: httpx.Response(200, json={"status": "failed", "error": TOKEN}))) as client:
        result = await client.call_tool("get_job", {"project_id": PROJECT, "job_id": str(uuid4())})
        assert not result.is_error and TOKEN not in content(result)


async def test_asset_upload_has_no_bearer_header_or_upload_url_result(tmp_path):
    (tmp_path / "cover.png").write_bytes(b"image bytes")
    requests = []

    async def handler(request):
        requests.append(request)
        if request.method == "POST":
            assert json.loads(request.content)["content_type"] == "image/png"
            return httpx.Response(201, json={"asset": {"id": "asset-1"},
                                           "upload_url": "https://storage.test/object?signature=secret"})
        assert "Authorization" not in request.headers
        assert await request.aread() == b"image bytes"
        assert request.headers["Content-Length"] == "11"
        return httpx.Response(200)

    async with Client(connector(handler, tmp_path)) as client:
        result = await client.call_tool("upload_asset", {"project_id": PROJECT, "path": "cover.png"})
    assert not result.is_error
    assert json.loads(content(result)) == {"asset": {"id": "asset-1"}}
    assert "signature" not in content(result)
    assert len(requests) == 2


async def test_audio_upload_completes_same_track_and_starts_processing(tmp_path):
    (tmp_path / "song.mp3").write_bytes(b"audio bytes")
    bodies = []

    def handler(request):
        if request.method == "PUT":
            return httpx.Response(200)
        body = json.loads(request.content)
        bodies.append(body)
        if request.url.path.endswith("/complete"):
            assert request.url.path.endswith(f"/{body['upload_id']}/complete")
            return httpx.Response(202, json={"id": body["upload_id"], "title": "Song"})
        return httpx.Response(201, json={"track_id": body["upload_id"], "upload_url": "https://storage.test/audio"})

    async with Client(connector(handler, tmp_path)) as client:
        result = await client.call_tool("upload_audio", {"path": "song.mp3"})
    assert not result.is_error
    assert bodies[0] == bodies[1]


async def test_local_upload_boundaries_and_disabled_default(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (tmp_path / "outside.png").write_bytes(b"outside")
    (media / "escape.png").symlink_to(tmp_path / "outside.png")
    (media / "token.txt").write_text(TOKEN)
    (media / "empty.png").touch()
    (media / "large.png").touch()
    with (media / "large.png").open("wb") as stream:
        stream.truncate(100 * 1024 * 1024 + 1)
    handler = lambda _: pytest.fail("Rejected local input must not call the API")
    async with Client(connector(handler, media)) as client:
        for path in ("../outside.png", "escape.png", "token.txt", "empty.png", "large.png", "missing.png", "https://other.test/image.png"):
            assert (await client.call_tool("upload_asset", {"project_id": PROJECT, "path": path})).is_error
    async with Client(connector(handler)) as client:
        assert (await client.call_tool("upload_audio", {"path": "song.mp3"})).is_error


@pytest.mark.parametrize("destination,status", [
    ("https://storage.test/asset?signature=secret", 403),
    ("https://storage.test/asset?signature=secret", 302),
    ("http://untrusted.test/asset?signature=secret", 200),
])
async def test_failed_or_unsafe_upload_returns_safe_error(tmp_path, destination, status):
    (tmp_path / "cover.png").write_bytes(b"image bytes")

    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, json={"asset": {"id": "asset-1"}, "upload_url": destination})
        return httpx.Response(status, headers={"Location": "https://another.test/asset"})

    async with Client(connector(handler, tmp_path)) as client:
        result = await client.call_tool("upload_asset", {"project_id": PROJECT, "path": "cover.png"})
    assert result.is_error
    assert "signature" not in content(result)


@pytest.mark.parametrize("url", ["http://remote.test/api/v1", "https://user:pass@studio.test", "https://studio.test/?token=secret", "file:///tmp/api"])
def test_reject_unsafe_configuration(url):
    with pytest.raises(ValueError):
        build_server(url, TOKEN)


def test_browser_schema_matches_python_contract():
    from pathlib import Path
    assert json.loads((Path(__file__).parents[1] / "browser/document.schema.json").read_text()) == Document.model_json_schema()
