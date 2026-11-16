import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "clipview_session";
const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Não autenticado." }, { status: 401 });

  try {
    const upstream = await fetch(`${API_URL}/projects`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Não foi possível conectar à API." }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Não autenticado." }, { status: 401 });

  try {
    if (request.headers.get("content-type")?.includes("application/json")) {
      const payload = await request.json();
      const upstream = await fetch(`${API_URL}/projects/import-url`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store"
      });
      const data = await upstream.json();
      return NextResponse.json(data, { status: upstream.status });
    }
    const incoming = await request.formData();
    const file = incoming.get("file");
    if (!(file instanceof File)) {
      return NextResponse.json({ detail: "Selecione um arquivo de vídeo." }, { status: 400 });
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      return NextResponse.json({ detail: "O vídeo excede o limite de 500 MB." }, { status: 413 });
    }

    const outgoing = new FormData();
    outgoing.append("file", file, file.name);
    const upstream = await fetch(`${API_URL}/projects/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: outgoing,
      cache: "no-store"
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Falha ao enviar o vídeo para a API." }, { status: 502 });
  }
}
