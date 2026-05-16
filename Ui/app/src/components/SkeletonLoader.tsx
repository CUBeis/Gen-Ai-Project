import { cn } from '@/lib/utils';

interface SkeletonLoaderProps {
  type?: 'text' | 'card' | 'avatar';
  lines?: number;
  className?: string;
}

export function SkeletonLoader({ type = 'text', lines = 3, className }: SkeletonLoaderProps) {
  if (type === 'avatar') {
    return (
      <div className={cn('w-12 h-12 rounded-full bg-gradient-to-r from-[rgba(0,49,31,0.06)] via-[rgba(0,49,31,0.1)] to-[rgba(0,49,31,0.06)] bg-[length:200%_100%] animate-shimmer', className)} />
    );
  }

  if (type === 'card') {
    return (
      <div className={cn('rounded-xl p-4 space-y-3', className)}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-[rgba(0,49,31,0.06)] via-[rgba(0,49,31,0.1)] to-[rgba(0,49,31,0.06)] bg-[length:200%_100%] animate-shimmer" />
          <div className="h-4 w-32 rounded bg-gradient-to-r from-[rgba(0,49,31,0.06)] via-[rgba(0,49,31,0.1)] to-[rgba(0,49,31,0.06)] bg-[length:200%_100%] animate-shimmer" />
        </div>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-3 rounded bg-gradient-to-r from-[rgba(0,49,31,0.06)] via-[rgba(0,49,31,0.1)] to-[rgba(0,49,31,0.06)] bg-[length:200%_100%] animate-shimmer"
            style={{ width: `${100 - i * 15}%` }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3.5 rounded bg-gradient-to-r from-[rgba(0,49,31,0.06)] via-[rgba(0,49,31,0.1)] to-[rgba(0,49,31,0.06)] bg-[length:200%_100%] animate-shimmer"
          style={{ width: `${100 - i * 20}%`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}
