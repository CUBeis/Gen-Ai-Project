import { Bell, MoreHorizontal } from 'lucide-react';
import { LanguageToggle } from '@/components/LanguageToggle';
import { IconButton } from '@/components/IconButton';

export function TopBar() {
  return (
    <header className="h-[60px] bg-nerve-bg/80 backdrop-blur-lg border-b border-[rgba(0,49,31,0.06)] flex items-center justify-between px-6 shrink-0 sticky top-0 z-30">
      <div>
        <h2 className="text-lg font-semibold text-nerve-dark">Care Conversation</h2>
        <p className="text-xs text-nerve-muted -mt-0.5">Ask about symptoms, medications, or health goals</p>
      </div>

      <div className="flex items-center gap-2">
        <LanguageToggle />
        <IconButton icon={Bell} badge />
        <IconButton icon={MoreHorizontal} />
      </div>
    </header>
  );
}
