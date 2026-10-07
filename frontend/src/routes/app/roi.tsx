import { Link } from "react-router-dom";

export function Roi() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">ROI forecast</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Hours x rate, capped against payroll. Payback, 3-year and 5-year return,
        with the working shown.
      </p>
      <div className="mt-6 grid gap-6 md:grid-cols-3">
        {[
          { label: "Payback", value: "18 months", blurb: "Investment divided by annual savings." },
          { label: "3-year ROI", value: "212%", blurb: " Compound savings over 3 years." },
          { label: "5-year ROI", value: "361%", blurb: " Compound savings over 5 years." },
        ].map((m) => (
          <article key={m.label} className="rounded-lg border border-line bg-cream p-5">
            <h3 className="text-sm uppercase tracking-[0.2em] text-muted-foreground">{m.label}</h3>
            <p className="mt-2 font-display text-4xl text-ink">{m.value}</p>
            <p className="mt-2 text-sm text-muted-foreground">{m.blurb}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
