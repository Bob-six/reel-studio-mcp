# Reel Studio MCP

MCP tools for creating and editing RezonAI reels, preparing lyrics, and rendering previews and exports. Rendering and storage run on the RezonAI backend.

## Hosted connection

Add `https://api.rezonai.ir/mcp` as a remote Streamable HTTP server in an OAuth-capable MCP client. Sign in to RezonAI in the browser and approve the requested Studio permissions. Tokens stay with the client; never paste them into chat. Connections can be revoked from the MCP guide in the reels page.

The hosted endpoint requires the corresponding backend OAuth release. Until deployed, it is unavailable. Upload local media through the web app: the hosted server cannot access your computer.

## Local connector

Install from this repository with `uv tool install git+https://github.com/Bob-six/reel-studio-mcp.git`, then launch `reel-studio-mcp` from a stdio MCP client. Configure `REEL_STUDIO_API_URL` (including `/api/v1`) and `REEL_STUDIO_TOKEN` through the client's private secret configuration. This operator-only mode is for people who already hold a website access token; it does not issue or refresh tokens. If you do not already have a token, use the hosted connection. Browser OAuth is provided by the hosted endpoint.

Set `REEL_STUDIO_MEDIA_ROOT` to a dedicated approved folder only if local uploads are needed. Uploads are disabled by default. Never commit tokens, signed links, private media or client secret configuration.

Call `studio_help` or read `studio://workflow` and `studio://schema` before editing. Fetch the latest project revision before a save, reconcile conflicts, render a preview, then export after approval. Tools never publish videos to social networks.

## Development

Run `uv sync`, `uv run pytest`, and `uv run ruff check src tests`. The tests mock API and storage traffic. Backend integration checks compare the copied document schemas to prevent contract drift.
