import assert from "node:assert/strict"
import { test } from "node:test"
import document from "./fixtures/document.json" with { type: "json" }
import { createStudioTools, modelContext, parseDocument, registerStudioTools } from "./index.js"

const actions = (extra = {}) => ({ listTracks: () => [], listProjects: () => [], openProject: () => {}, createProject: () => {}, ...extra })
test("uses document API, supports older navigator API and absent browser support", () => {
  const context = {}
  assert.equal(modelContext({ document: { modelContext: context } }), context)
  assert.equal(modelContext({ navigator: { modelContext: context } }), context)
  assert.equal(modelContext({}), null)
})
test("document schema validates full drafts and rejects malformed nested input", () => {
  const doc = parseDocument(document)
  assert.ok(Array.isArray(doc.layers))
  assert.ok(doc.background)
  assert.equal(doc.version, 1)
  assert.throws(() => parseDocument({}))
  assert.throws(() => parseDocument({ ...document, layers: "bad" }))
  assert.throws(() => parseDocument({ ...document, layers: [{ id: "x", kind: "text", x: -1 }] }))
})
test("tool validation happens before application callbacks and errors do not expose secrets", async () => {
  let called = 0
  const tools = createStudioTools(actions({ openProject: () => { called++; throw new Error("secret token") } }))
  const open = tools.find(tool => tool.name === "open_project")
  assert.ok((await open.execute({ project_id: "../private" })).isError)
  assert.equal(called, 0)
  const result = await open.execute({ project_id: "11111111-1111-1111-1111-111111111111" })
  assert.equal(called, 1)
  assert.ok(result.isError)
  assert.ok(!JSON.stringify(result).includes("secret token"))
  assert.equal(tools.some(tool => tool.name === "update_document"), false)
})
test("editor tool applies a validated document and previews by default", async () => {
  let changed, preview
  const tools = createStudioTools(actions({ getProject: () => ({}), updateDocument: value => { changed = value }, renderProject: value => { preview = value.preview } }))
  const update = tools.find(tool => tool.name === "update_document")
  assert.ok(!(await update.execute({ edit_version: 3, document })).isError)
  assert.equal(changed.edit_version, 3)
  assert.equal(changed.document.version, 1)
  await tools.find(tool => tool.name === "render_project").execute({})
  assert.equal(preview, true)
})
test("registration abort unregisters only owned tools and late calls fail", async () => {
  const controller = new AbortController(), tools = new Map()
  const context = { registerTool: tool => { tools.set(tool.name, tool) }, unregisterTool: name => tools.delete(name) }
  await registerStudioTools(context, actions(), controller.signal)
  assert.equal(tools.size, 5)
  const help = tools.get("studio_help")
  controller.abort()
  assert.equal(tools.size, 0)
  await assert.rejects(help.execute({}), /closed/)
})
test("failed registration removes previously registered tools", async () => {
  const tools = new Map(), controller = new AbortController()
  const context = { registerTool: tool => { if (tools.size) throw new Error("denied"); tools.set(tool.name, tool) }, unregisterTool: name => tools.delete(name) }
  await assert.rejects(registerStudioTools(context, actions(), controller.signal), /denied/)
  assert.equal(tools.size, 0)
})
test("rapid unmount and remount do not unregister the next page's tools", async () => {
  const tools = new Map()
  const context = { registerTool: tool => { tools.set(tool.name, tool) }, unregisterTool: name => tools.delete(name) }
  const oldPage = new AbortController(), newPage = new AbortController()
  const first = registerStudioTools(context, actions(), oldPage.signal)
  oldPage.abort()
  const second = registerStudioTools(context, actions(), newPage.signal)
  await Promise.all([first, second])
  assert.equal(tools.size, 5)
  newPage.abort()
  assert.equal(tools.size, 0)
})
test("an async duplicate does not unregister an existing owner's tool", async () => {
  const existing = { name: "studio_help" }, tools = new Map([["studio_help", existing]])
  const context = { async registerTool() { throw new Error("duplicate") }, unregisterTool: name => tools.delete(name) }
  await assert.rejects(registerStudioTools(context, actions(), new AbortController().signal), /duplicate/)
  assert.equal(tools.get("studio_help"), existing)
})
test("a pending legacy registration is removed after it resolves following abort", async () => {
  const tools = new Map(), controller = new AbortController()
  let complete
  const context = { registerTool: tool => new Promise(resolve => { complete = () => { tools.set(tool.name, tool); resolve() } }), unregisterTool: name => tools.delete(name) }
  const registration = registerStudioTools(context, actions(), controller.signal)
  await new Promise(resolve => setTimeout(resolve, 0))
  controller.abort()
  complete()
  await registration
  assert.equal(tools.size, 0)
})
test("partial replacement documents cannot reset omitted current values", async () => {
  let called = false
  const tools = createStudioTools(actions({ getProject: () => ({}), updateDocument: () => { called = true } }))
  const result = await tools.find(tool => tool.name === "update_document").execute({ edit_version: 1, document: { background: {}, layers: [] } })
  assert.equal(result.isError, true)
  assert.equal(called, false)
})
