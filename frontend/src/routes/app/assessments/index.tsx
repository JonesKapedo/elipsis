import { Link } from "react-router-dom";

export function AssessmentsList() {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl text-ink">Assessments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Start or continue an organisational readiness assessment.
          </p>
        </div>
        <Link to="/app/assessments/new" className="inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-medium text-paper transition hover:-translate-y-0.5">
          + New assessment
        </Link>
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[
          { title: "Demo Logistics Ltd", subtitle: "Logistics / Freight & Distribution", status: "Completed", score: 78 },
          { title: "Sample Org", subtitle: "Demo + sample data", status: "In progress", score: 42 },
        ].map((a) => (
          <article key={a.title} className="rounded-lg border border-line bg-cream p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display text-xl text-ink">{a.title}</h3>
                <p className="text-sm text-muted-foreground">{a.subtitle}</p>
              </div>
              <span className="rounded-full bg-good/10 px-3 py-1 text-xs font-medium text-good">{a.status}</span>
            </div>
            <div className="mt-4 flex items centerline justify-between text-sm">
              <span className="text-muted-foreground">Maturity</span>
              <span className="font-display text-2xl tabular-nums text-steel">{a.score}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-line max-w-full">
              <div className="h-full rounded-full bg-steel2" style={{ width: `${a.score}%` }} />
            </div>
            <Link to="/app/assessments/new" className="mt-3 text-sm text-steel2 transition hover:underline">
              Open assessment →
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}
