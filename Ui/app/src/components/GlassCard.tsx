import { cn } from '@/lib/utils';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'glass' | 'elevated' | 'dark' | 'default';
}

export function GlassCard({ children, className, variant = 'glass' }: GlassCardProps) {
  const variants = {
    glass: 'glass',
    elevated: 'bg-[#FFF7E6] shadow-elevated border border-[rgba(0,49,31,0.08)]',
    dark: 'bg-[#00311F] text-[#FFF7E6]',
    default: 'bg-[#FFF3D5] border border-[rgba(0,49,31,0.08)]',
  };

  return (
    <div className={cn('rounded-2xl p-6', variants[variant], className)}>
      {children}
    </div>
  );
}
