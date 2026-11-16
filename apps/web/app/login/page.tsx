"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Falha no login.");
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link className="auth-brand" href="/"><span className="brand-mark">C</span>ClipView</Link>
        <div className="eyebrow">Bem-vindo de volta</div>
        <h1>Entre na sua conta</h1>
        <p className="subheading">Acesse seu estúdio e continue criando.</p>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="email">E-mail</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />
          <label htmlFor="password">Senha</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} />
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="primary auth-submit" disabled={busy}>{busy ? "Entrando..." : "Entrar"}</button>
        </form>
        <p className="auth-switch">Ainda não tem conta? <Link href="/register">Criar conta</Link></p>
      </section>
    </main>
  );
}
