import { useAppStore } from '@/store/useAppStore';

export function useDirection() {
  const direction = useAppStore((s) => s.direction);
  const language = useAppStore((s) => s.language);
  const toggleDirection = useAppStore((s) => s.toggleDirection);
  const isRTL = direction === 'rtl';

  return { direction, language, isRTL, toggleDirection };
}
