import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "clipview_session";

export async function GET(
  request: NextRequest,
  context: { params: { projectId: string } }
) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Não autenticado." }, { status: 401 });

  const projectId = context.params.projectId;
  if (!/^\\d+$/.test(projectId)) {
    return NextResponse.json({ detail: "Projeto inválido." }, { status: 400 });
  }

  const headers = new Headers({ Authorization: `Bearer ${token}` });
  const range = request.headers.get("range");
  const ifRange = request.headers.get("if-range");
  if (range) headers.set("Range", range);
  if (ifRange) headers.set("If-Range", ifRange);

  try {
    const upstream = await fetch(`${API_URL}/projects/${projectId}/video`, {
      headers,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-length", "content-range", "accept-ranges", "last-modified", "etag", "content-disposition", "cache-control"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ detail: "Não foi possível reproduzir o vídeo." }, { status: 502 });
  }
}
