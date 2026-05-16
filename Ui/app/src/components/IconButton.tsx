import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { LucideIcon } from 'lucide-react';

interface IconButtonProps {
  icon: LucideIcon;
  onClick?: () => void;
  className?: string;
  variant?: 'ghost' | 'filled';
  size?: 'sm' | 'md';
  badge?: boolean;
}

export function IconButton({
  icon: Icon,
  onClick,
  className,
  variant = 'ghost',
  size = 'md',
  badge = false,
}: IconButtonProps) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onClick}
      className={cn(
        'relative rounded-xl transition-all duration-200 hover:bg-[rgba(77,105,78,0.1)] hover:text-nerve-green',
        sizeClasses[size],
        variant === 'filled' && 'bg-nerve-bg-secondary',
        className
      )}
    >
      <Icon className={cn('text-nerve-dark', size === 'sm' ? 'w-4 h-4' : 'w-5 h-5')} />
      {badge && (
        <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
      )}
    </Button>
  );
}
