import { useEffect, useRef } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { randomInsights } from '@/data/mockData';

let globalEventCount = 0;

function getRandomDelay() {
  return Math.floor(Math.random() * 8000) + 8000; // 8-16s
}

function generateMockEvent() {
  const types = ['schedule_updated', 'insight_generated', 'notification'] as const;
  const type = types[Math.floor(Math.random() * types.length)];

  switch (type) {
    case 'insight_generated': {
      const insight = randomInsights[Math.floor(Math.random() * randomInsights.length)];
      return { type, payload: { ...insight, id: `insight-${Date.now()}` } };
    }
    case 'schedule_updated':
      return {
        type,
        payload: { id: `s${Math.floor(Math.random() * 3) + 2}`, status: 'completed' as const },
      };
    case 'notification':
      return {
        type,
        payload: { message: 'Care plan updated with new recommendations.', type: 'info' as const },
      };
  }
}

export function useWebSocket(enabled = true) {
  const setConnected = useAppStore((s) => s.setWsConnected);
  const addInsight = useAppStore((s) => s.addInsight);
  const updateScheduleItem = useAppStore((s) => s.updateScheduleItem);
  const addToast = useAppStore((s) => s.addToast);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isRunning = useRef(false);

  useEffect(() => {
    if (!enabled || isRunning.current) return;
    isRunning.current = true;
    setConnected(true);

    const scheduleNext = () => {
      if (!isRunning.current) return;
      timeoutRef.current = setTimeout(() => {
        if (!isRunning.current) return;
        globalEventCount++;
        // Only fire events occasionally, max 8 total
        if (globalEventCount <= 8) {
          const event = generateMockEvent();
          if (event.type === 'insight_generated') {
            addInsight(event.payload as Parameters<typeof addInsight>[0]);
            addToast({ message: 'New health insight available', type: 'info' });
          } else if (event.type === 'schedule_updated') {
            updateScheduleItem(
              event.payload.id as string,
              { status: event.payload.status }
            );
          } else if (event.type === 'notification') {
            addToast({
              message: (event.payload.message as string) || 'Update received',
              type: 'info',
            });
          }
        }
        scheduleNext();
      }, getRandomDelay());
    };

    scheduleNext();

    return () => {
      isRunning.current = false;
      setConnected(false);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [enabled, setConnected, addInsight, updateScheduleItem, addToast]);

  return { connected: useAppStore((s) => s.wsConnected) };
}
