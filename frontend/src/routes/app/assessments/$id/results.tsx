import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PILLARS } from '../../../../lib/elipsis';

export function AssessmentResult() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/assessments/${id}/results`)
      .then((r) => r.json())
      .then(setResult)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !result) return <div className='p-6 text-muted-foreground'>Loading results&hellip;</div>;

  const maturity = result.maturity ?? {};

  return (
    <div className='p-6'>
      <h1 className='font-display text-3xl text-ink'>Assessment results</h1>
      <p className='mt-1 text-sm text-muted-foreground'>
        Org: {result.orgName ?? 'Demo Logistics Ltd'} · {new Date(result.completedAt ?? '').toLocaleDateString()}
      </p>

      <div className='mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-[11px] uppercase tracking-[0.2em] text-muted-foreground'>Elipsis Index</p>
          <p className='mt-2 font-display text-4xl tabular-nums text-ink'>{result.index ?? 0}</p>
          <p className='mt-1 text-xs text-muted-foreground'>{maturity.label ?? 'Reactive'}</p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-[11px] uppercase tracking-[0.2em] text-muted-foreground'>Automation opportunity</p>
          <p className='mt-2 font-display text-4xl tabular-nums text-ink'>{result.composites?.opportunity ?? 0}</p>
          <p className='mt-1 text-xs text-muted-foreground'>of 100</p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-[11px] uppercase tracking-[0.2em] text-muted-foreground'>Modelled savings</p>
          <p className='mt-2 font-display text-4xl tabular-nums text-ink'>
            {result.roi?.annualSavings ? new Intl.NumberFormat('en-ZA', { style: 'currency', currency: (result.roi?.currency ?? 'USD'), maximumFractionDigits: 0 }).format(result.roi.annualSavings) : '0'}
          </p>
          <p className='mt-1 text-xs text-muted-foreground'>{result.roi?.paybackMonths ?? 0} mo payback</p>
        </div>
        <div className='rounded-lg border border-line bg-cream p-5'>
          <p className='text-[11px] uppercase tracking-[0.2em] text-muted-foreground'>Confidence</p>
          <p className='mt-2 font-display text-4xl tabular-nums text-ink'>{result.confidence ?? 0}%</p>
          <p className='mt-1 text-xs text-muted-foreground'>of survey completeness</p>
        </div>
      </div>

      <div className='mt-8'>
        <h2 className='font-display text-2xl text-ink'>Pillars</h2>
        <div className='mt-4 grid gap-4 md:grid-cols-2'>
          {PILLARS.map((pillar) => {
            const p = result.pillars?.find((x: any) => x.code === pillar.code);
            const score = p?.score ?? 0;
            return (
              <article key={pillar.code} className='rounded-lg border border-line bg-cream p-5'>
                <div className='flex items-start justify-between'>
                  <div>
                    <p className='text-[11px] uppercase tracking-[0.2em] text-muted-foreground'>{pillar.code} · {Math.round(pillar.weight * 100)}%</p>
                    <h3 className='mt-1 font-display text-xl text-ink'>{pillar.label}</h3>
                    <p className='text-sm text-muted-foreground'>{pillar.objective}</p>
                  </div>
                  <span className='font-display text-3xl tabular-nums text-steel'>{score}</span>
                </div>
                <div className='mt-3 h-2 rounded-full bg-line max-w-full'>
                  <div className='h-full rounded-full bg-steel2' style={{ width: `${score}%` }} />
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
