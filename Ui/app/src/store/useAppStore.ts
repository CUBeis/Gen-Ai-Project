import { create } from 'zustand';
import type { Message, ScheduleItem, Medication, Insight, Toast, Direction, Language, AppView } from '@/types';

interface AppState {
  direction: Direction;
  language: Language;
  sidebarCollapsed: boolean;
  activeView: AppView;
  messages: Message[];
  isTyping: boolean;
  schedule: ScheduleItem[];
  medications: Medication[];
  insights: Insight[];
  toasts: Toast[];
  wsConnected: boolean;

  toggleDirection: () => void;
  setLanguage: (lang: Language) => void;
  toggleSidebar: () => void;
  setActiveView: (view: AppView) => void;
  addMessage: (msg: Message) => void;
  setTyping: (typing: boolean) => void;
  clearChat: () => void;
  addScheduleItem: (item: ScheduleItem) => void;
  updateScheduleItem: (id: string, updates: Partial<ScheduleItem>) => void;
  addMedication: (med: Medication) => void;
  updateMedication: (id: string, updates: Partial<Medication>) => void;
  addInsight: (insight: Insight) => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;
  setWsConnected: (connected: boolean) => void;
}

let toastIdCounter = 0;

export const useAppStore = create<AppState>((set) => ({
  direction: 'ltr',
  language: 'en',
  sidebarCollapsed: false,
  activeView: 'Chat',
  messages: [],
  isTyping: false,
  schedule: [],
  medications: [],
  insights: [],
  toasts: [],
  wsConnected: false,

  toggleDirection: () =>
    set((state) => {
      const newDir = state.direction === 'ltr' ? 'rtl' : 'ltr';
      const newLang = newDir === 'rtl' ? 'ar' : 'en';
      document.documentElement.dir = newDir;
      document.documentElement.lang = newLang;
      return { direction: newDir, language: newLang };
    }),

  setLanguage: (lang) =>
    set(() => {
      const newDir = lang === 'ar' ? 'rtl' : 'ltr';
      document.documentElement.dir = newDir;
      document.documentElement.lang = lang;
      return { language: lang, direction: newDir };
    }),

  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setActiveView: (view) => set({ activeView: view }),

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  setTyping: (typing) => set({ isTyping: typing }),

  clearChat: () => set({ messages: [], isTyping: false }),

  addScheduleItem: (item) => set((state) => ({ schedule: [...state.schedule, item] })),

  updateScheduleItem: (id, updates) =>
    set((state) => ({
      schedule: state.schedule.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    })),

  addMedication: (med) =>
    set((state) => {
      const exists = state.medications.some((m) => m.name === med.name);
      if (exists) return state;
      return { medications: [med, ...state.medications] };
    }),

  updateMedication: (id, updates) =>
    set((state) => ({
      medications: state.medications.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),

  addInsight: (insight) =>
    set((state) => {
      const exists = state.insights.some((i) => i.title === insight.title);
      if (exists) return state;
      return { insights: [insight, ...state.insights] };
    }),

  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: `toast-${++toastIdCounter}` }],
    })),

  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
