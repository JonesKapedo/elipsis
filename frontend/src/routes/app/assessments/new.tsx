import { useState } from "react";

export function AssessmentsNew() {
  const [org, setOrg] = useState("Demo Logistics Ltd");
  const [industry, setIndustry] = useState("Logistics");
  const [subIndustry, setSubIndustry] = useState("Freight & Distribution");
  const [headcount, setHeadcount] = useState(120);
  const [annualRevenue, setAnnualRevenue] = useState(12000000);
  const [hourlyRate, setHourlyRate] = useState(18);
  const [currency, setCurrency] = useState("USD");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/v1/assessments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ org, industry, subIndustry, headcount, annualRevenue, hourlyRate, currency }),
    });
    if (res.ok) {
      window.location.href = "/app/assessments";
    } else {
      alert("Failed to create assessment");
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="font-display text-3xl text-ink">New assessment</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Set up your organisation profile to generate a baseline readiness score.
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-5 rounded-lg border border-line bg-cream p-6">
        <div>
          <label className="block text-sm font-medium text-ink">Organization name</label>
          <input value={org} onChange={(e) => setOrg(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm" />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-ink">Industry</label>
            <select value={industry} onChange={(e) => setIndustry(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm">
              {["Logistics","Financial Services","Manufacturing","Healthcare","Retail","Telecommunications","Energy","Public Sector","Technology","Agriculture","Hospitality"].map((i) => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-ink">Sub-industry</label>
            <select value={subIndustry} onChange={(e) => setSubIndustry(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm">
              {["Freight & Distribution","Banking","Insurance","Manufacturing","Clinical Services","E-commerce","Oil & Gas","Government","Software","Crop Production","Hospitality"].map((i) => <option key={i}>{i}</option>)}
            </select>
          </div>
        </div>
        <div className="grid gap-5 sm:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-ink">Headcount</label>
            <input type="number" value={headcount} onChange={(e) => setHeadcount(Number(e.target.value))} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink">Annual revenue</label>
            <input type="number" value={annualRevenue} onChange={(e) => setAnnualRevenue(Number(e.target.value))} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink">Hourly rate</label>
            <input type="number" value={hourlyRate} onChange={(e) => setHourlyRate(Number(e.target.value))} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-ink">Currency</label>
          <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="mt-1 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm">
            {["USD","EUR","GBP","ZAR","KES","NGN"].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <button type="submit" className="inline-flex h-12 w-full items-center justify-center rounded-md bg-ink px-4 text-sm font-medium text-paper transition hover:-translate-y-0.5 hover:shadow">
          Start assessment
        </button>
      </form>
    </div>
  );
}
