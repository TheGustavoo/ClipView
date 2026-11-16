import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "clipview_session";

export async function GET(
  request: NextRequest,
  context: { params: { jobId: string } }
) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Não autenticado." }, { status: 401 });

  const jobId = context.params.jobId;
  if (!/^\d+$/.test(jobId)) {
    return NextResponse.json({ detail: "Tarefa inválida." }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_URL}/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Não foi possível conectar à API." }, { status: 502 });
  }
}
