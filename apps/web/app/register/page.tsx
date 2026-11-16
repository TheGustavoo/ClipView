"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Falha no cadastro.");
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível criar a conta.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link className="auth-brand" href="/"><span className="brand-mark">C</span>ClipView</Link>
        <div className="eyebrow">Seu estúdio começa aqui</div>
        <h1>Crie sua conta</h1>
        <p className="subheading">Cadastre-se para organizar seus projetos de vídeo.</p>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="name">Nome</label>
          <input id="name" type="text" autoComplete="name" minLength={2} maxLength={80} required value={name} onChange={e => setName(e.target.value)} />
          <label htmlFor="email">E-mail</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />
          <label htmlFor="password">Senha</label>
          <input id="password" type="password" autoComplete="new-password" minLength={10} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} />
          <small className="auth-hint">Use pelo menos 10 caracteres.</small>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="primary auth-submit" disabled={busy}>{busy ? "Criando conta..." : "Criar conta"}</button>
        </form>
        <p className="auth-switch">Já tem uma conta? <Link href="/login">Entrar</Link></p>
      </section>
    </main>
  );
}
