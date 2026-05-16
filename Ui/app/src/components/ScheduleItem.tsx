import { Pill, Activity, TrendingUp, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ScheduleItem as ScheduleItemType } from '@/types';

const iconMap: Record<string, React.ElementType> = {
  pill: Pill,
  activity: Activity,
  'trending-up': TrendingUp,
};

const statusConfig = {
  completed: { icon: CheckCircle2, className: 'text-green-500', lineClass: 'line-through opacity-60' },
  upcoming: { icon: Clock, className: 'text-nerve-muted', lineClass: '' },
  pending: { icon: Clock, className: 'text-nerve-muted opacity-50', lineClass: 'opacity-50' },
  current: { icon: Clock, className: 'text-nerve-green', lineClass: 'border-l-[3px] border-l-nerve-green bg-[rgba(77,105,78,0.05)]' },
};

export function ScheduleItemComponent({ item }: { item: ScheduleItemType }) {
  const Icon = iconMap[item.icon] || Activity;
  const StatusIcon = statusConfig[item.status].icon;
  const config = statusConfig[item.status];

  return (
    <div className={cn(
      'flex items-center gap-3 py-2.5 px-2 rounded-lg transition-all duration-200',
      config.lineClass
    )}>
      <span className="text-xs font-semibold text-nerve-muted w-[70px] shrink-0">{item.time}</span>
      <div className="w-7 h-7 rounded-full bg-nerve-green/10 flex items-center justify-center shrink-0">
        <Icon className="w-3.5 h-3.5 text-nerve-green" />
      </div>
      <span className={cn('text-sm font-medium text-nerve-dark flex-1', config.lineClass)}>
        {item.title}
      </span>
      <StatusIcon className={cn('w-4 h-4 shrink-0', config.className)} />
    </div>
  );
}
