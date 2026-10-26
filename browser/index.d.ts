export type Input = Record<string, unknown>
export type Action = (input: Input) => unknown | Promise<unknown>
export type StudioActions = {
  listTracks: Action
  listProjects: Action
  openProject: Action
  createProject: Action
  getProject?: Action
  getSource?: Action
  updateDocument?: Action
  setSource?: Action
  saveProject?: Action
  prepareLyrics?: Action
  renderProject?: Action
  getJob?: Action
}
export interface BrowserTool {
  name: string
  description: string
  inputSchema: Input
  annotations: { readOnlyHint: boolean }
  execute(input?: Input): Promise<{ content: { type: "text"; text: string }[]; isError?: boolean }>
}
export interface ModelContext {
  registerTool(tool: BrowserTool, options?: { signal: AbortSignal }): void | Promise<void>
  unregisterTool?(name: string): void
}
export function modelContext(scope?: unknown): ModelContext | null
export function createStudioTools(actions: StudioActions): BrowserTool[]
export function registerStudioTools(context: ModelContext | null, actions: StudioActions, signal: AbortSignal): Promise<void>
export function parseDocument(input: unknown): unknown
export const documentSchema: Input
