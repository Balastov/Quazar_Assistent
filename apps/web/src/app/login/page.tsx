"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setTokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@quazar.local");
  const [password, setPassword] = useState("admin12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api<{ access_token: string; refresh_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setTokens(data.access_token, data.refresh_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-quazar-bg">
      <form onSubmit={handleSubmit} className="w-full max-w-md p-8 bg-quazar-panel rounded-2xl border border-quazar-border">
        <h1 className="text-2xl font-bold mb-2">Quazar Assistent</h1>
        <p className="text-quazar-muted mb-6">Войдите в корпоративный AI-ассистент</p>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        <label className="block mb-4">
          <span className="text-sm text-quazar-muted">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full px-4 py-2 rounded-lg bg-quazar-bg border border-quazar-border focus:outline-none focus:border-quazar-accent"
          />
        </label>
        <label className="block mb-6">
          <span className="text-sm text-quazar-muted">Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full px-4 py-2 rounded-lg bg-quazar-bg border border-quazar-border focus:outline-none focus:border-quazar-accent"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-quazar-accent hover:bg-quazar-accentHover text-white font-medium disabled:opacity-50"
        >
          {loading ? "Вход..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
