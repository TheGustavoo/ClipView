import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "clipview_session";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Não autenticado." }, { status: 401 });

  try {
    const upstream = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    });
    const data = await upstream.json();
    if (!upstream.ok) {
      const response = NextResponse.json(
        { detail: data.detail ?? "Sessão inválida." },
        { status: upstream.status }
      );
      response.cookies.delete(COOKIE_NAME);
      return response;
    }
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ detail: "Não foi possível conectar à API." }, { status: 502 });
  }
}
