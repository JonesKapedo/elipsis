import { Link } from "react-router-dom";

export function Departments() {
  return (
    <div className="p-6">
      <h1 className="font-display text-3xl text-ink">Organisation</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Division and department structure used for segmentation.
      </p>
      <div className="mt-6 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {[
          { name: "Operations", code: "OPS" },
          { name: "Finance", code: "FIN" },
          { name: "Human Resources", code: "HR" },
        ].map((d) => (
          <div key={d.code} className="rounded-lg border border-line bg-cream p-5">
            <p className="font-display text-xl text-ink">{d.name}</p>
            <p className="text-xs text-muted-foreground">{d.code}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
