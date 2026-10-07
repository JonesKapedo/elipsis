import { useState, useEffect } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";

export function AppShell() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("elipsis_token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    fetch("/api/v1/auth/me")
      .then((r) => r.json())
      .then((d: { name?: string; email?: string }) => setUser({ name: d.name ?? d.email ?? "Admin", email: d.email ?? "" }))
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) return <div className="grid min-h-screen place-items-center bg-paper text-sm text-muted-foreground">Restoring session…</div>;
  if (!user) return <div className="min-h-screen bg-paper flex items-center justify-center"><div className="text-muted-foreground">Please sign in to continue.</div></div>;

  const nav = [
    { to: "/app", label: "Command centre" },
    { to: "/app/assessments", label: "Assessments" },
    { to: "/app/automation", label: "Discovery" },
    { to: "/app/roadmap", label: "Roadmap" },
    { to: "/app/roi", label: "ROI" },
    { to: "/app/benchmarks", label: "Benchmarks" },
    { to: "/app/advisor", label: "Advisor" },
  ];

  return (
    <div className="min-h-screen bg-paper text-ink lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-line bg-navy text-paper lg:min-h-screen lg:border-b-0 lg:border-r lg:border-line-dark">
        <div className="flex items-center justify-between px-5 py-5">
          <Link to="/" className="font-display text-xl">Elipsis</Link>
          <div className="lg:hidden"></div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible lg:px-3">
          {nav.map((item) => {
            const active = item.to === "/app" ? window.location.pathname === "/app" : window.location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`whitespace-nowrap rounded-md px-3 py-2 text-sm ${active ? "bg-navy-3" : "text-mist hover:text-paper"}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden px-5 py-6 lg:block">
          <p className="text-[11px] uppercase tracking-[0.18em] text-mist">{user.email}</p>
          <div className="mt-3">
            <button onClick={() => { localStorage.removeItem("elipsis_token"); navigate("/login"); }} className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-paper transition">Sign out</button>
          </div>
        </div>
      </aside>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  );
}
