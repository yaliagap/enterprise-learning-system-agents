export const dynamic = "force-dynamic";
export const runtime = "edge";

import { type NextRequest } from "next/server";

const FOUNDRY_URL = process.env.FOUNDRY_AGENT_URL!;
const FOUNDRY_API_KEY = process.env.FOUNDRY_API_KEY!;

export async function POST(request: NextRequest) {
  if (!FOUNDRY_URL || !FOUNDRY_API_KEY) {
    return new Response(JSON.stringify({ error: "Foundry not configured" }), { status: 503 });
  }

  const body = await request.arrayBuffer();

  const upstream = await fetch(FOUNDRY_URL, {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("Content-Type") ?? "application/json",
      "api-key": FOUNDRY_API_KEY,
      "Foundry-Features": "HostedAgents=V1Preview",
      "Accept": "text/event-stream",
    },
    body,
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
      "Transfer-Encoding": "chunked",
    },
  });
}
