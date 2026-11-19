import os from 'node:os';
import { pathToFileURL } from 'node:url';

const packages = os.homedir() + '/.local/share/reaper-mcp/node_modules';
const { Client } = await import(pathToFileURL(packages + '/@modelcontextprotocol/sdk/dist/esm/client/index.js'));
const { StdioClientTransport } = await import(pathToFileURL(packages + '/@modelcontextprotocol/sdk/dist/esm/client/stdio.js'));
const client = new Client({ name: 'tame-kanye-session', version: '1.0' });
const transport = new StdioClientTransport({
  command: '/opt/homebrew/bin/node',
  args: [packages + '/@mthines/reaper-mcp/main.js', 'serve'],
  env: { ...process.env, REAPER_MCP_TELEMETRY: '0' },
  stderr: 'pipe'
});

export async function call(name, args = {}) {
  const response = await client.callTool({ name, arguments: args }, undefined, { timeout: 45000 });
  const message = response.content[0]?.text;
  if (response.isError) throw Error(name + ': ' + message);
  let data;
  try { data = JSON.parse(message); } catch { data = message; }
  if (data?.error || data?.ok === false) throw Error(name + ': ' + message);
  return data;
}

export async function withReaper(run) {
  await client.connect(transport);
  try { return await run(); } finally { await client.close(); }
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const [, , name, args] = process.argv;
  await withReaper(async () => console.log(JSON.stringify(await call(name, args ? JSON.parse(args) : {}), null, 2)));
}
