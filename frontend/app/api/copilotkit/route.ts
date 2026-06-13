// This route is no longer used — the frontend connects directly to the
// FastAPI AG-UI backend via @ag-ui/client (see app/hooks/useAgentChat.ts).
export function GET() {
  return new Response(JSON.stringify({ status: "deprecated" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

export function POST() {
  return new Response(JSON.stringify({ status: "deprecated" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
