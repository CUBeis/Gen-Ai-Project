import { useRef, useEffect, useCallback } from 'react';

export function useAutoScroll<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null);

  const scrollToBottom = useCallback(() => {
    if (ref.current) {
      ref.current.scrollTo({
        top: ref.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom, ...deps]);

  return { ref, scrollToBottom };
}
