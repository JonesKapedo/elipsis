import { Link } from "react-router-dom";

export function Benchmarks() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">Benchmarks</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Industry, size-band and peer percentile comparisons.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Industry avg", value: "46", sub: "based on 2,000 companies" },
          { label: "Size band avg", value: "48", sub: "adjusted for headcount" },
          { label: "Digital avg", value: "49", sub: "across all industries" },
          { label: "Automation avg", value: "44", sub: "benchmarked" },
        ].map((b) => (
          <article key={b.label} className="rounded-lg border border-line bg-cream p-5">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{b.label}</p>
            <p className="mt-2 font-display text-3xl text-ink">{b.value}</p>
            <p className="text-xs text-muted-foreground">{b.sub}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
