import { ReactNode } from 'react';
export interface CardProps { children: ReactNode; className?: string; }
export function Card({ children, className = '' }: CardProps) {
  return <div className={`rounded-lg border border-line bg-cream p-5 ${className}`}>{children}</div>;
}
