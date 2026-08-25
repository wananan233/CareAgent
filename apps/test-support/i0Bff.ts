import { spawn, type ChildProcess } from 'node:child_process'
import { once } from 'node:events'
import { createServer } from 'node:net'
import { resolve } from 'node:path'

export const i0Tokens = { elderA: 'i0-elder-a', familyA: 'i0-family-a', elderB: 'i0-elder-b', familyB: 'i0-family-b' }

const delay = (milliseconds: number) => new Promise<void>((resolveDelay) => setTimeout(resolveDelay, milliseconds))
const redact = (value: string) => Object.values(i0Tokens).reduce((text, token) => text.replaceAll(token, '[REDACTED]'), value).slice(-4_000)

async function reservePort(): Promise<number> {
  return new Promise<number>((resolvePort, reject) => {
    const server = createServer()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address() as { port: number }
      server.close((error) => error ? reject(error) : resolvePort(address.port))
    })
  })
}

async function terminate(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null || child.signalCode !== null) return
  const exited = once(child, 'exit').then(() => undefined)
  child.kill('SIGTERM')
  await Promise.race([exited, delay(2_000)])
  if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL')
}

export async function startI0Bff(): Promise<{ baseUrl: string; stop: () => Promise<void> }> {
  const port = await reservePort()
  let logs = ''
  const child: ChildProcess = spawn('python', ['-m', 'scripts.run_i0_bff'], { cwd: resolve(process.cwd(), '../..'), env: { ...process.env, CAREHUB_I0_BFF_PORT: String(port), CAREHUB_I0_ELDER_A_TOKEN: i0Tokens.elderA, CAREHUB_I0_FAMILY_A_TOKEN: i0Tokens.familyA, CAREHUB_I0_ELDER_B_TOKEN: i0Tokens.elderB, CAREHUB_I0_FAMILY_B_TOKEN: i0Tokens.familyB }, stdio: ['ignore', 'pipe', 'pipe'] })
  child.stdout?.on('data', (chunk: Buffer) => { logs += chunk.toString() })
  child.stderr?.on('data', (chunk: Buffer) => { logs += chunk.toString() })
  const baseUrl = `http://127.0.0.1:${port}`
  const deadline = Date.now() + 10_000
  try {
    while (Date.now() < deadline) {
      if (child.exitCode !== null) throw new Error(`I0 BFF 提前退出（code=${child.exitCode}）：${redact(logs)}`)
      try { const r = await fetch(`${baseUrl}/v1/households`, { headers: { Authorization: `Bearer ${i0Tokens.familyA}` } }); const body = await r.json() as { items?: Array<{ household_id?: string }> }; if (r.ok && body.items?.some(item => item.household_id === 'household:i0-a')) return { baseUrl, stop: () => terminate(child) } } catch { /* 启动期间继续轮询；总超时保留脱敏诊断。 */ }
      await delay(50)
    }
    throw new Error(`I0 BFF readiness 超时：${redact(logs)}`)
  } catch (error) {
    await terminate(child)
    throw error
  }
}
