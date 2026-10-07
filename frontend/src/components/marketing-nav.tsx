import { Link } from 'react-router-dom';
export function MarketingNav() {
  return (
    <header className='border-b border-line bg-paper'>
      <div className='mx-auto flex h-16 max-w-6xl items-center justify-between px-6'>
        <Link to='/' className='font-display text-xl text-ink'>Elipsis</Link>
        <nav className='hidden gap-6 md:flex'>
          <Link to='/login' className='text-sm text-muted-foreground hover:text-ink transition'>Sign in</Link>
          <Link to='/login' className='text-sm font-medium text-steel2 transition hover:underline'>Start assessment</Link>
        </nav>
      </div>
    </header>
  );
}
