import { cn } from '@/lib/utils';

export function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <div className="flex items-center gap-2 bg-[rgba(255,247,230,0.8)] rounded-lg px-3 py-1.5">
      <span className={cn(
        'w-2 h-2 rounded-full animate-pulse-dot',
        connected ? 'bg-green-500' : 'bg-red-400'
      )} />
      <span className="text-[11px] text-nerve-muted font-medium">
        {connected ? 'Live Updates' : 'Disconnected'}
      </span>
    </div>
  );
}
