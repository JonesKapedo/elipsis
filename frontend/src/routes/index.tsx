import { Link } from "react-router-dom";
import { PILLARS } from "../lib/elipsis";

export function Home() {
  return (
    <main>
      <section className="relative overflow-hidden bg-navy text-paper">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
          <p className="text-[11px] uppercase tracking-[0.32em] text-steel2">Business transformation intelligence</p>
          <h1 className="mt-4 max-w-3xl font-display text-5xl leading-[1.05] md:text-7xl">
            Measure. Transform. Scale.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-relaxed text-paper/80 md:text-lg">
            Discover how ready your organisation is for AI, automation, and digital
            transformation — then turn that score into a roadmap, a budget, and a
            return.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/login" className="inline-flex h-12 items-center rounded-md bg-paper px-6 text-sm font-medium text-navy shadow-soft transition hover:-translate-y-0.5 hover:shadow">
              Start assessment
            </Link>
            <Link to="/login" className="inline-flex h-12 items-center rounded-md border border-line-dark px-6 text-sm text-paper transition hover:bg-linedark">
              View sample report
            </Link>
          </div>
        </div>
      </section>

      <section id="pillars" className="bg-paper text-ink">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <p className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Seven transformation pillars</p>
          <h2 className="mt-3 max-w-2xl font-display text-4xl">Not a questionnaire. A measurement model.</h2>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Sixty-three questions, twenty-one subdomains, thirty-six executive
            metrics. Each pillar is weighted. Each answer is a number a board can
            act on.
          </p>
          <div className="mt-10 grid gap-3 md:grid-cols-2">
            {PILLARS.map((p) => (
              <article key={p.code} className="flex items-start justify-between gap-4 rounded-lg border border-line bg-cream p-5">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    {p.code} · {Math.round(p.weight * 100)}%
                  </p>
                  <h3 className="mt-1 font-display text-2xl">{p.label}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{p.objective}</p>
                </div>
                <p className="font-display text-3xl tabular-nums text-steel">—</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-cream text-ink">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="grid gap-6 md:grid-cols-3">
            {[
              { n: "01", t: "Assessment", d: "ORG-001, segmented into 21 short steps. Live scoring. Autosave. Department-aware." },
              { n: "02", t: "Analytics", d: "Current state, future readiness, risk, opportunity, and a five-level maturity model." },
              { n: "03", t: "Discovery", d: "Every low score becomes a pain point with impact, solution, complexity and owner." },
              { n: "04", t: "ROI forecast", d: "Hours x rate, capped against payroll. Payback, 3-year and 5-year return, with the working shown." },
              { n: "05", t: "Roadmap", d: "30 / 90 / 180 / 365 / 730 day plans. Benefit, difficulty, resources, KPIs." },
              { n: "06", t: "Board reports", d: "Executive, departmental, health, automation, investment priority, and benchmark packs." },
            ].map(({ n, t, d }) => (
              <article key={n} className="rounded-lg border border-line bg-cream p-6 no-print">
                <span className="font-display text-3xl">{n}</span>
                <h3 className="mt-2 font-display text-xl">{t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-navy">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="flex flex-col justify-between gap-8 md:flex-row md:items-end">
            <div>
              <p className="text-[11px] uppercase tracking-[0.28em] text-steel2">For operators, not spectators</p>
              <h2 className="mt-3 max-w-xl font-display text-4xl">Consulting-grade insight, without a 14-week slide factory.</h2>
              <p className="mt-4 text-paper/80">
                Every low score becomes a named pain point, a recommended programme,
                and a modelled return. Brought to you by the people who built the
                measurement model behind the industry's most respected readiness
                frameworks.
              </p>
            </div>
            <Link to="/login" className="inline-flex h-12 items-center rounded-md bg-paper px-6 text-sm font-medium text-navy shadow-soft transition hover:-translate-y-0.5 hover:shadow">
              Open the platform
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
