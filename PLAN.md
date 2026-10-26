# Public Reel Studio MCP

1. Extract the connector, schemas and protocol tests into this repository with clean history.
2. Add hosted Streamable HTTP transport in RezonAI, using the same tools.
3. Add OAuth authorization code flow with S256 PKCE, browser consent through existing login, hashed opaque tokens, rotating refresh tokens and revocation.
4. Enforce private user projects and source access. Retain the shared staff workspace. Use the existing subscription tier limits for upload size and processing allowance; cap user projects at 100 and preparation/render jobs at 30 per day, with at most two preparation and render jobs combined active per user.
5. Replace browser-token instructions with the hosted URL, consent and connected-app revocation.
6. Test protocol compatibility, isolation, OAuth failures, rotation and revocation; publish the repository and open integration PRs.

Acceptance: a signed-in user authorizes a client without copying a token, edits only accessible projects, renders within limits, and can revoke the connection. Hosted tools cannot upload local machine files; use the web app for those uploads. The local stdio connector retains opt-in local uploads.

Package registry publication needs registry credentials; Git-source installation is sufficient for the first release. Keep existing staff access while deploying backend and frontend together.
