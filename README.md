# Reel Studio browser tools

Use an AI agent alongside the open RezonAI Reel Studio page. Browser tools use the page's existing sign-in, editor draft, Undo history and autosave. Users do not copy tokens or configure a hosted MCP endpoint.

Keep Studio open and use a browser agent that supports WebMCP. The page registers tools through `document.modelContext`, with a fallback for browsers exposing the older `navigator.modelContext` API. WebMCP is experimental; an ordinary remote MCP client cannot connect to a webpage URL as though it were a hosted MCP server.

Tools list sources and projects, open or create projects, read the live draft, replace a validated document using its `edit_version`, select a source, save, prepare lyrics, render and inspect jobs. Upload files through the page's file picker. Previews are the default; the page asks for confirmation before a full export.

Rendering, storage and processing continue through the existing RezonAI API. This package adds no backend MCP server or OAuth service. Server authorization and account limits still apply.

## Integrate

Install the browser package from Git:

```sh
npm install github:Bob-six/reel-studio-mcp
```

The host application provides callbacks for its existing operations:

```js
import { modelContext, registerStudioTools } from '@rezonai/reel-studio-webmcp'

const controller = new AbortController()
await registerStudioTools(modelContext(), actions, controller.signal)
// On leaving Studio or signing out:
controller.abort()
```

`actions` implements `StudioActions` from `browser/index.d.ts`. Register the base actions on the project library, and include editor actions only while a project is open. Read the current draft for every call, including unsaved edits. Reject stale edit versions and locked-layer changes in the host callback. Use the host's normal save/conflict and job flows. The document validator checks structure; the host must also check timing, source duration and asset ownership.

If WebMCP is absent or registration fails, keep normal editor operation available and explain that the browser agent cannot use the tools. Do not expose credentials to agents or return raw API errors.

## Development

Run `npm ci && npm test` for the browser adapter. The checked-in document JSON schema comes from the Python model; `uv sync && uv run pytest` checks parity and the existing stdio connector.

The Python stdio connector remains available for operators who already hold an API token. It is an optional legacy interface; its source is in `src/reel_studio_mcp`. It does not provide browser sign-in or renew tokens. Browser users do not need Python or this connector.
