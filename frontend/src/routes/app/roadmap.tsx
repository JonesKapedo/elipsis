import { Link } from "react-router-dom";

export function Roadmap() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">Roadmap</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        30 / 90 / 180 / 365 / 730 day plans. Benefit, difficulty, resources, KPIs.
      </p>
      <div className="mt-6 space-y-4">
        {[
          { id: "30d", label: "30-Day Plan", days: "30 days", focus: "Stabilise and capture obvious waste." },
          { id: "90d", label: "90-Day Plan", days: "90 days", focus: "Automate repetitive, rule-based work." },
          { id: "6m", label: "6-Month Plan", days: "180 days", focus: "Rebuild the operating flow: approvals, integrations, controls." },
        ].map((h) => (
          <div key={h.id} className="rounded-lg border border-line bg-cream p-5">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-xl text-ink">{h.label}</h3>
              <span className="text-sm text-muted-foreground">{h.days}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{h.focus}</p>
            <div className="mt-3 flex gap-3 text-sm">
              <span className="text-muted-foreground">Benefit: modelled programme</span>
              <span className="text-muted-foreground">Investment: step-by-step</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
