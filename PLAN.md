# Browser-first public Reel Studio tools

1. Publish reusable browser tool definitions, document schemas and lifecycle handling in this repository.
2. Register tools in the open Studio library and editor using WebMCP. Reuse the signed-in page's API client and live editor state.
3. Apply document changes through Undo/autosave, reject stale edit versions, preserve locked layers, and reuse existing preparation/rendering flows. Confirm full exports in the page.
4. Keep customer projects private. Customers can select their own tracks; archived library songs remain unavailable. Use account upload limits, at most 100 projects, and at most 30 preparation/render jobs combined per rolling day with two active jobs combined. Marketing and admin users keep their shared staff projects, without access to customer projects.
5. Replace copied-token instructions with browser compatibility, tool availability and open-page requirements. Test live edits, cleanup, account changes and invalid inputs.

Acceptance: a browser agent edits the visible draft without copied tokens or a second login. Users can see and undo changes. Closing Studio or signing out removes its tools. Unsupported browsers retain the normal editor. Rendering continues on the existing backend.

Hosted MCP and separate OAuth were deferred in favor of browser-first use. The Python connector remains optional for existing operators. Package-registry publication is separate; Git installation is sufficient for the first release.
