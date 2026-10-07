import { forwardRef, ButtonHTMLAttributes, Ref, ReactNode } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const variantStyles = {
  primary: 'bg-ink text-paper hover:-translate-y-0.5 hover:shadow transition',
  secondary: 'border border-line bg-cream text-ink hover:bg-linedark transition',
  ghost: 'text-muted-foreground hover:text-paper hover:bg-linedark transition',
};

const sizeStyles = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = 'primary', size = 'md', className = '', type = 'button', disabled, onClick, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled}
        onClick={onClick}
        className={`inline-flex h-10 items-center justify-center rounded-md font-medium transition ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...rest}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

