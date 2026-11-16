"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type User = { id: number; name: string; email: string };
type Project = {
  id: number;
  title: string;
  original_filename: string;
  size_bytes: number;
  content_type: string;
  status: string;
  created_at: string;
  processing_job_id?: number | null;
};
type ClipSuggestion = { start: number; end: number; duration: number; score: number; text: string; reasons: string[] };
type Job = { status: string; transcript: string | null; language: string | null; error_message: string | null; clip_suggestions: ClipSuggestion[] | null };

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    uploaded: "Enviado", queued: "Na fila", processing: "Analisando vídeo", ready: "Pronto", completed: "Transcrição concluída", transcribing: "Transcrevendo áudio", extracting_audio: "Extraindo áudio",
    queue_unavailable: "Fila indisponível", processing_failed: "Falha no processamento",
  };
  return labels[status] ?? status;
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRefs = useRef<Record<number, HTMLVideoElement | null>>({});
  const [previewEnds, setPreviewEnds] = useState<Record<number, number>>({});
  const [selectedVideo, setSelectedVideo] = useState<File | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Record<number, Job>>({});
  const [clipDrafts, setClipDrafts] = useState<Record<string, { start: string; end: string }>>({});
  const [savingClip, setSavingClip] = useState<string | null>(null);
  const [editorMessage, setEditorMessage] = useState("");
  const [checking, setChecking] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/auth/me", { cache: "no-store" })
      .then(async response => {
        if (!response.ok) throw new Error("Sessão ausente");
        return response.json();
      })
      .then(data => { if (active) setUser(data); })
      .catch(() => { if (active) router.replace("/login"); })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, [router]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    const loadProjects = async () => {
      try {
        const response = await fetch("/api/projects", { cache: "no-store" });
        const data: Project[] = await response.json();
        if (!response.ok) throw new Error("Não foi possível carregar projetos.");
        if (!active) return;
        setProjects(data);
        const jobEntries = await Promise.all(data.filter(project => project.processing_job_id).map(async project => {
          const jobResponse = await fetch(`/api/jobs/${project.processing_job_id}`, { cache: "no-store" });
          if (!jobResponse.ok) return null;
          return [project.id, await jobResponse.json()] as const;
        }));
        if (active) setJobs(Object.fromEntries(jobEntries.filter((entry): entry is NonNullable<typeof entry> => entry !== null)));
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Erro ao carregar projetos.");
      }
    };
    void loadProjects();
    const timer = window.setInterval(loadProjects, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [user]);

  function previewClip(projectId: number, start: number, end: number) {
    const video = videoRefs.current[projectId];
    if (!video) return;
    video.currentTime = start;
    setPreviewEnds(current => ({ ...current, [projectId]: end }));
    void video.play().catch(() => setEditorMessage("Não foi possível iniciar a reprodução. Tente usar os controles do vídeo."));
  }

  function handlePreviewTimeUpdate(projectId: number, video: HTMLVideoElement) {
    const end = previewEnds[projectId];
    if (end !== undefined && video.currentTime >= end) {
      video.pause();
      setPreviewEnds(current => {
        const next = { ...current };
        delete next[projectId];
        return next;
      });
    }
  }

  async function saveClip(projectId: number, jobId: number, clipIndex: number, clip: ClipSuggestion) {
    const key = `${jobId}-${clipIndex}`;
    const draft = clipDrafts[key] ?? { start: String(clip.start), end: String(clip.end) };
    const start = Number(draft.start);
    const end = Number(draft.end);
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
      setEditorMessage("Confira os tempos: o fim precisa ser maior que o início.");
      return;
    }
    setSavingClip(key);
    setEditorMessage("");
    try {
      const response = await fetch(`/api/jobs/${jobId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clip_index: clipIndex, start, end }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Não foi possível salvar o corte.");
      setJobs(current => ({ ...current, [projectId]: { ...current[projectId], clip_suggestions: data.clip_suggestions } }));
      setClipDrafts(current => ({ ...current, [key]: { start: String(start), end: String(end) } }));
      setEditorMessage("Tempos do corte salvos.");
    } catch (err) {
      setEditorMessage(err instanceof Error ? err.message : "Falha ao salvar o corte.");
    } finally {
      setSavingClip(null);
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedVideo(file);
    setError("");
    setMessage("");
  }

  async function uploadVideo() {
    if (!selectedVideo) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const body = new FormData();
      body.append("file", selectedVideo);
      const response = await fetch("/api/projects", { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Não foi possível enviar o vídeo.");
      setProjects(current => [data, ...current]);
      setSelectedVideo(null);
      if (fileRef.current) fileRef.current.value = "";
      setMessage("Vídeo enviado! Ele entrou na fila de análise automática.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no upload.");
    } finally {
      setUploading(false);
    }
  }

  if (checking || !user) {
    return <main className="auth-page"><div className="auth-loading">Carregando seu estúdio...</div></main>;
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">C</div><span className="brand-name">ClipView</span></div>
        <div>
          <div className="nav-label">Workspace</div>
          <nav className="nav">
            <a className="active" href="#"><span>▦</span><span>Visão geral</span></a>
            <a href="#projects"><span>▤</span><span>Meus projetos</span></a>
            <a href="#upload"><span>＋</span><span>Novo vídeo</span></a>
          </nav>
        </div>
        <div>
          <div className="nav-label">Conta</div>
          <nav className="nav">
            <a href="#usage"><span>◈</span><span>Créditos</span></a>
            <a href="#settings"><span>⚙</span><span>Configurações</span></a>
          </nav>
        </div>
        <div className="sidebar-bottom">
          <strong>Seu estúdio de vídeos</strong>
          <p>Transforme conteúdos longos em clipes prontos para suas redes.</p>
          <span className="eyebrow">ClipView beta</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">Seu espaço de criação</div>
            <h1>Olá, {user.name.split(" ")[0]}</h1>
            <p className="subheading">Organize seus vídeos e prepare seus próximos clipes.</p>
          </div>
          <div className="profile-actions">
            <span className="profile-email">{user.email}</span>
            <div className="avatar" aria-label="Perfil">{user.name.slice(0, 1).toUpperCase()}</div>
            <button className="logout-button" onClick={logout}>Sair</button>
          </div>
        </header>

        <section className="stats" id="usage" aria-label="Resumo da conta">
          <div className="stat"><span>Projetos criados</span><strong>{projects.length}</strong><small>Projetos da sua conta</small></div>
          <div className="stat"><span>Vídeos processados</span><strong>{projects.filter(project => project.status === "ready").length}</strong><small>Vídeos com transcrição concluída</small></div>
          <div className="stat"><span>Créditos disponíveis</span><strong>—</strong><small>Planos e créditos serão conectados em breve</small></div>
        </section>

        <section id="upload">
          <div className="section-head"><h2>Comece um novo projeto</h2><span>Etapa 1 de 3 · adicionar vídeo</span></div>
          <div className="upload">
            <div className="upload-icon">↑</div>
            <h3>Envie um vídeo para seu estúdio</h3>
            <p>MP4, MOV, WebM ou MKV · até 500 MB por arquivo.</p>
            <input ref={fileRef} className="file-input" type="file" accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
              onChange={handleFile} />
            <div className="upload-actions">
              <button className="secondary" onClick={() => fileRef.current?.click()} disabled={uploading}>Selecionar vídeo</button>
              <button className="primary" onClick={uploadVideo} disabled={!selectedVideo || uploading}>{uploading ? "Enviando..." : "Enviar vídeo"}</button>
            </div>
            {selectedVideo && <div className="file-name" role="status">{selectedVideo.name} · {formatBytes(selectedVideo.size)}</div>}
            {message && <div className="upload-success" role="status">{message}</div>}
            {error && <div className="auth-error" role="alert">{error}</div>}
          </div>
        </section>

        <section id="projects">
          <div className="section-head"><h2>Projetos recentes</h2><span>{projects.length} projeto(s)</span></div>
          <div className="projects">
            {projects.length === 0 ? (
              <div className="project">
                <div className="project-info"><div className="thumb">▶</div><div><div className="project-title">Nenhum projeto ainda</div><div className="project-meta">Envie seu primeiro vídeo para começar.</div></div></div>
                <span className="status">Aguardando vídeo</span>
              </div>
            ) : projects.map(project => (
              <div className="project" key={project.id}>
                <div className="project-info">
                  <div className="thumb">▶</div>
                  <div>
                    <div className="project-title">{project.title}</div>
                    <div className="project-meta">{project.original_filename} · {formatBytes(project.size_bytes)}</div>
                    <div className="video-preview">
                      <video
                        ref={element => { videoRefs.current[project.id] = element; }}
                        src={`/api/projects/${project.id}/video`}
                        controls
                        preload="metadata"
                        playsInline
                        onTimeUpdate={event => handlePreviewTimeUpdate(project.id, event.currentTarget)}
                        onPause={() => setPreviewEnds(current => { if (current[project.id] === undefined) return current; const next = { ...current }; delete next[project.id]; return next; })}
                      />
                      <span>Prévia do vídeo original</span>
                    </div>
                    {jobs[project.id]?.transcript && <div className="transcript-preview">Transcrição ({jobs[project.id].language ?? "idioma detectado"}): {jobs[project.id].transcript}</div>}
                    {jobs[project.id]?.clip_suggestions?.length && project.processing_job_id ? <div className="clip-suggestions"><strong>Editor de cortes sugeridos</strong>{jobs[project.id].clip_suggestions.map((clip, index) => { const key = `${project.processing_job_id}-${index}`; const draft = clipDrafts[key] ?? { start: String(clip.start), end: String(clip.end) }; return <div className="clip-suggestion" key={`${clip.start}-${index}`}><div className="clip-suggestion-top"><b>Corte {index + 1}</b><span>{formatTime(clip.start)}–{formatTime(clip.end)} · {Math.round(clip.score * 100)} pts</span></div><div className="clip-timing-fields"><label>Início (seg.)<input type="number" min="0" step="0.1" value={draft.start} onChange={event => setClipDrafts(current => ({ ...current, [key]: { ...draft, start: event.target.value } }))} /></label><label>Fim (seg.)<input type="number" min="0" step="0.1" value={draft.end} onChange={event => setClipDrafts(current => ({ ...current, [key]: { ...draft, end: event.target.value } }))} /></label><button className="secondary clip-save" onClick={() => saveClip(project.id, project.processing_job_id!, index, clip)} disabled={savingClip === key}>{savingClip === key ? "Salvando..." : "Salvar tempos"}</button><button className="secondary clip-save" onClick={() => previewClip(project.id, Number(draft.start), Number(draft.end))}>Pré-visualizar corte</button></div><p>{clip.text}</p><small>{clip.reasons.join(" · ")}</small></div>; })}{editorMessage && <div className="editor-message" role="status">{editorMessage}</div>}</div> : null}
                    {jobs[project.id]?.error_message && <div className="project-meta">{jobs[project.id].error_message}</div>}
                  </div>
                </div>
                <span className="status">{statusLabel(project.status)}</span>
              </div>
            ))}
          </div>
        </section>

        <p className="footer-note" id="settings">Os vídeos enviados são armazenados no servidor e associados à sua conta. As sugestões iniciais de cortes são baseadas na transcrição. Análise visual de reações, edição e renderização dos clipes ainda estão em desenvolvimento.</p>
      </main>
    </div>
  );
}
