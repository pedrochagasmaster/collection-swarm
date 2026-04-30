import fs from "node:fs"
import { Agent } from "@cursor/sdk"

/**
 * Stdin JSON: { "messages": { "role","content" }[], "modelId": string, "cwd": string, "preamble": string }
 * Stdout JSON: { "content", "inputTokens", "outputTokens", "status" } | { "error": string }
 */
function formatMessages(messages, preamble) {
  const lines = [preamble.trim(), "", "## Messages"]
  for (const m of messages) {
    lines.push(`### ${m.role}`, m.content, "")
  }
  return lines.join("\n")
}

async function main() {
  const raw = fs.readFileSync(0, "utf8")
  let payload
  try {
    payload = JSON.parse(raw)
  } catch (e) {
    console.log(JSON.stringify({ error: `invalid JSON stdin: ${e}` }))
    process.exitCode = 1
    return
  }

  const apiKey = process.env.CURSOR_API_KEY
  if (!apiKey) {
    console.log(JSON.stringify({ error: "CURSOR_API_KEY is not set" }))
    process.exitCode = 1
    return
  }

  const { messages, modelId, cwd, preamble } = payload
  if (!Array.isArray(messages) || !modelId || typeof preamble !== "string") {
    console.log(JSON.stringify({ error: "expected messages[], modelId, and preamble" }))
    process.exitCode = 1
    return
  }

  const workspace = typeof cwd === "string" && cwd.length > 0 ? cwd : process.cwd()
  const prompt = formatMessages(messages, preamble)

  let agent
  try {
    agent = await Agent.create({
      apiKey,
      name: "collection-swarm",
      model: { id: modelId },
      local: { cwd: workspace },
    })
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    console.log(JSON.stringify({ error: message }))
    process.exitCode = 1
    return
  }

  try {
    const run = await agent.send(prompt)
    let content = ""
    for await (const event of run.stream()) {
      if (event.type !== "assistant") continue
      for (const block of event.message.content) {
        if (block.type === "text") content += block.text
      }
    }
    const result = await run.wait()
    const usage = result.usage ?? {}
    const inputTokens = Number(usage.inputTokens ?? 0)
    const outputTokens = Number(usage.outputTokens ?? 0)
    console.log(
      JSON.stringify({
        content,
        inputTokens,
        outputTokens,
        status: result.status,
      }),
    )
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    console.log(JSON.stringify({ error: message }))
    process.exitCode = 1
  } finally {
    if (agent && typeof agent[Symbol.asyncDispose] === "function") {
      await agent[Symbol.asyncDispose]()
    }
  }
}

await main()
