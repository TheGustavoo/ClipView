"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type User = { id: number; name: string; email: string };

export default function Home() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

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

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  function handleFile(file?: File) {
    if (file) setSelectedFile(file.name);
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
          <div className="stat"><span>Projetos criados</span><strong>0</strong><small>Seus projetos aparecerão aqui</small></div>
          <div className="stat"><span>Vídeos processados</span><strong>0</strong><small>Pronto para começar</small></div>
          <div className="stat"><span>Créditos disponíveis</span><strong>—</strong><small>Planos e créditos serão conectados em breve</small></div>
        </section>

        <section id="upload">
          <div className="section-head"><h2>Comece um novo projeto</h2><span>Etapa 1 de 3 · adicionar vídeo</span></div>
          <div className="upload">
            <div className="upload-icon">↑</div>
            <h3>Escolha um vídeo para começar</h3>
            <p>Selecione um arquivo do seu dispositivo. O upload real será habilitado na próxima etapa.</p>
            <input ref={fileRef} className="file-input" type="file" accept="video/*"
              onChange={event => handleFile(event.target.files?.[0])} />
            <button className="primary" onClick={() => fileRef.current?.click()}>Selecionar vídeo</button>
            {selectedFile && <div className="file-name" role="status">Arquivo selecionado: {selectedFile}</div>}
          </div>
        </section>

        <section id="projects">
          <div className="section-head"><h2>Projetos recentes</h2><span>Seus trabalhos aparecerão aqui</span></div>
          <div className="projects">
            <div className="project">
              <div className="project-info"><div className="thumb">▶</div><div><div className="project-title">Nenhum projeto ainda</div><div className="project-meta">Adicione seu primeiro vídeo para começar.</div></div></div>
              <span className="status">Aguardando vídeo</span>
            </div>
          </div>
        </section>

        <p className="footer-note" id="settings">Sua sessão é protegida por cookie HttpOnly. O seletor de vídeo ainda não envia arquivos: armazenamento, processamento de vídeo, IA e créditos estão em desenvolvimento.</p>
      </main>
    </div>
  );
}
