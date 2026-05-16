import { Globe } from 'lucide-react';
import { useDirection } from '@/hooks/useDirection';
import { cn } from '@/lib/utils';

interface LanguageToggleProps {
  className?: string;
}

export function LanguageToggle({ className }: LanguageToggleProps) {
  const { toggleDirection, language } = useDirection();

  return (
    <button
      onClick={toggleDirection}
      className={cn(
        'flex items-center gap-1.5 text-xs font-semibold text-nerve-muted hover:text-nerve-green transition-colors duration-200',
        className
      )}
    >
      <Globe className="w-4 h-4" />
      <span>{language === 'en' ? 'EN' : 'AR'}</span>
    </button>
  );
}
