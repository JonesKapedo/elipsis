import { ReactNode } from 'react';
export interface ScoreRingProps { score: number; label: string; max?: number; }
export function ScoreRing({ score, label, max = 100 }: ScoreRingProps) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100));
  return (
    <div className='flex flex-col items-center'>
      <div className='relative h-32 w-32'>
        <svg className='transform -rotate-90' viewBox='0 0 100 100'>
          <circle cx='50' cy='50' r='42' fill='none' stroke='var(--color-line)' strokeWidth='12' />
          <circle cx='50' cy='50' r='42' fill='none' stroke='var(--color-steel2)' strokeWidth='12' strokeLinecap='round' strokeDasharray={pct + ' 100'} />
        </svg>
        <div className='absolute inset-0 flex flex-col items-center justify-center'>
          <span className='font-display text-3xl tabular-nums text-ink'>{Math.round(pct)}</span>
          <span className='text-xs text-muted-foreground'>{label}</span>
        </div>
      </div>
    </div>
  );
}
