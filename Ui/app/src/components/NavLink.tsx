import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface NavLinkProps {
  icon: LucideIcon;
  label: string;
  active?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}

export function NavLink({ icon: Icon, label, active = false, collapsed = false, onClick }: NavLinkProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 h-12 px-3.5 rounded-xl transition-all duration-200 relative group',
        active
          ? 'bg-[rgba(77,105,78,0.12)] text-nerve-green'
          : 'text-nerve-muted hover:bg-[rgba(77,105,78,0.08)] hover:text-nerve-dark'
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-nerve-green rounded-r-full" />
      )}
      <Icon className="w-[22px] h-[22px] shrink-0" />
      {!collapsed && (
        <span className="text-[15px] font-medium truncate">{label}</span>
      )}
      {collapsed && (
        <span className="absolute left-full ml-2 px-2.5 py-1 bg-nerve-dark text-white text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap z-50">
          {label}
        </span>
      )}
    </button>
  );
}
