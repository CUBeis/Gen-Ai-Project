import { Pill, Calendar, Sparkles, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const iconMap: Record<string, React.ElementType> = {
  pill: Pill,
  calendar: Calendar,
  sparkles: Sparkles,
  'alert-circle': AlertCircle,
};

interface QuickActionChipProps {
  label: string;
  icon: string;
  onClick: () => void;
}

export function QuickActionChip({ label, icon, onClick }: QuickActionChipProps) {
  const Icon = iconMap[icon] || Sparkles;

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium',
        'bg-[rgba(77,105,78,0.08)] border border-[rgba(77,105,78,0.15)]',
        'text-nerve-dark hover:bg-[rgba(77,105,78,0.15)] hover:border-nerve-green',
        'transition-all duration-200'
      )}
    >
      <Icon className="w-4 h-4 text-nerve-green" />
      {label}
    </button>
  );
}
