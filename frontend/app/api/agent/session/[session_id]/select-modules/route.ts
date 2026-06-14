export const dynamic = "force-dynamic";

import { type NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: { session_id: string } }
) {
  const { session_id } = params;
  const body = await request.arrayBuffer();

  const upstream = await fetch(
    `${BACKEND_URL}/session/${session_id}/select-modules`,
    {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("Content-Type") ?? "application/json",
      },
      body,
    }
  );

  const data = await upstream.json();
  return new Response(JSON.stringify(data), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
