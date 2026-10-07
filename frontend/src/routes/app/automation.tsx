import { Link } from "react-router-dom";

export function Automation() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">Discovery</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Every low score becomes a pain point with impact, solution, complexity,
        automation owner and horizon.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[
          { code: "OPS", title: "Standardise processes", desc: "Document core jobs into searchable SOPs." },
          { code: "WFL", title: "Reduce waiting time", desc: "Map handoffs and remove bottlenecks." },
          { code: "REP", title: "Automate repetition", desc: "Identify rules-based tasks for software." },
        ].map((p) => (
          <article key={p.code} className="rounded-lg border border-line bg-cream p-5">
            <p className="text-[11px] uppercase tracking-[0.2em] text-steel2">{p.code}</p>
            <h3 className="mt-1 font-display text-xl text-ink">{p.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{p.desc}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
