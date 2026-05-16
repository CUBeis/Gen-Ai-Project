import type { LucideIcon } from 'lucide-react';

interface TrustBadgeProps {
  icon: LucideIcon;
  label: string;
}

export function TrustBadge({ icon: Icon, label }: TrustBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-4 h-4 text-nerve-green" />
      <span className="text-xs font-medium text-nerve-muted">{label}</span>
    </div>
  );
}
