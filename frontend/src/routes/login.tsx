import { useState } from "react";
import { Link } from "react-router-dom";

export function Login() {
  const [email, setEmail] = useState("admin@elipsis.local");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors([]);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        window.location.href = "/app";
        return;
      }
      const body = (await res.json()) as { detail?: string };
      setErrors(body.detail ? [body.detail] : ["Login failed"]);
    } catch {
      setErrors(["Could not reach the server"]);
    }
  }

  return (
    <main className="min-h-screen bg-paper flex flex-col">
      <div className="mx-auto flex w-full max-w-md flex-col items-center px-6 pt-14 pb-10">
        <p className="text-[11px] uppercase tracking-[0.32em] text-steel2">Sign in to Elipsis</p>
        <h1 className="mt-3 max-w-md font-display text-3xl text-ink">
          Measure. Transform. Scale.
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Your organisation's transformation intelligence. Secure console for
evaluated teams.
        </p>
        <form onSubmit={onSubmit} className="mt-8 w-full space-y-4" noValidate>
          <label>
            <span className="block text-sm font-medium text-ink">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="mt-1 w-full rounded-md border border-input bg-cream px-3 py-2.5 text-sm text-ink placeholder:text-muted-foreground focus:border-steel focus:outline-none focus:ring-2 focus:ring-steel/20"
              required
            />
          </label>
          <label>
            <span className="block text-sm font-medium text-ink">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="mt-1 w-full rounded-md border border-input bg-cream px-3 py-2.5 text-sm text-ink placeholder:text-muted-foreground focus:border-steel focus:outline-none focus:ring-2 focus:ring-steel/20"
              required
            />
          </label>
          {errors.length > 0 && (
            <div className="rounded-md bg-risk/10 p-3 text-sm text-destructive">
              {errors.map((e) => <div key={e}>{e}</div>)}
            </div>
          )}
          <button type="submit" className="inline-flex h-12 w-full items-center justify-center rounded-md bg-ink px-4 text-sm font-medium text-paper transition hover:-translate-y-0.5 hover:shadow">
            Sign in
          </button>
        </form>
        <p className="mt-6 text-sm text-muted-foreground">
          Need access? Contact your administrator.
        </p>
      </div>
    </main>
  );
}
