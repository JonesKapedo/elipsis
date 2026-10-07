import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export function AssessmentReport() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/assessments/${id}/report`)
      .then((r) => r.json())
      .then(setResult)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !result) return <div className='p-6 text-muted-foreground'>Loading report&hellip;</div>;

  const roi = result.roi ?? {};

  return (
    <div className='p-6'>
      <h1 className='font-display text-3xl text-ink'>Boardroom report</h1>
      <p className='mt-1 text-sm text-muted-foreground'>
        Org: {result.orgName ?? 'Demo Logistics Ltd'}
      </p>

      <div className='mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-3'>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>Net year 1</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>
            {roi.netYear1 ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (roi.currency ?? 'USD'), maximumFractionDigits: 0 }).format(roi.netYear1) : '0'}
          </p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>3-year value</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>
            {roi.threeYearValue ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (roi.currency ?? 'USD'), maximumFractionDigits: 0 }).format(roi.threeYearValue) : '0'}
          </p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>5-year value</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>
            {roi.fiveYearValue ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (roi.currency ?? 'USD'), maximumFractionDigits: 0 }).format(roi.fiveYearValue) : '0'}
          </p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>3-year ROI</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>{roi.roi3 ?? 0}%</p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>5-year ROI</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>{roi.roi5 ?? 0}%</p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-xs uppercase tracking-[0.2em] text-muted-foreground'>Payback</p>
          <p className='mt-2 font-display text-3xl tabular-nums text-ink'>{roi.paybackMonths ?? 0} mo</p>
        </div>
      </div>

      <div className='mt-8'>
        <h2 className='font-display text-2xl text-ink'>Roadmap</h2>
        <div className='mt-4 space-y-4'>
          {result.roadmap?.map((h: any) => (
            <div key={h.id} className='rounded-lg border border-line bg-cream p-5'>
              <div className='flex items-center justify-between'>
                <h3 className='font-display text-xl text-ink'>{h.label}</h3>
                <span className='text-sm text-muted-foreground'>{h.days} days</span>
              </div>
              <p className='mt-2 text-sm text-muted-foreground'>{h.focus}</p>
              <div className='mt-3 grid gap-3 sm:grid-cols-2'>
                <div className='rounded bg-paper p-3 text-sm'>
                  <p className='text-[11px] uppercase tracking-[0.18em] text-muted-foreground'>Benefit</p>
                  <p className='font-display text-xl text-steel'>{h.benefit ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (result.roi?.currency ?? 'USD'), maximumFractionDigits: 0 }).format(h.benefit) : '0'}</p>
                </div>
                <div className='rounded bg-paper p-3 text-sm'>
                  <p className='text-[11px] uppercase tracking-[0.18em] text-muted-foreground'>Investment</p>
                  <p className='font-display text-xl text-steel2'>{h.investment ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (result.roi?.currency ?? 'USD'), maximumFractionDigits: 0 }).format(h.investment) : '0'}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
