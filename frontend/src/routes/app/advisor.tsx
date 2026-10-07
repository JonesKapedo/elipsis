import { Link } from "react-router-dom";

export function Advisor() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">AI Transformation Advisor</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Curated guidance on the highest-impact opportunities behind your score,
        with benchmark context and investment prioritisation.
      </p>
      <div className="mt-6 rounded-lg border border-line bg-cream p-5">
        <h3 className="font-display text-xl text-ink">Discovered opportunities</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          AI-adoption readiness score, automation potential, and the programmes
          that will move the needle fastest.
        </p>
        <Link to="/app/assessments/new" className="mt-3 inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-medium text-paper transition">
          Open advisor →
        </Link>
      </div>
    </div>
  );
}
