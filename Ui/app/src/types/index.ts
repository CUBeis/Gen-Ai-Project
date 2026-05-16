export interface Message {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: Date;
  type?: 'text' | 'medication' | 'schedule' | 'insight';
  embeddedData?: Medication | ScheduleItem | Insight;
}

export interface ScheduleItem {
  id: string;
  time: string;
  title: string;
  icon: string;
  status: 'completed' | 'upcoming' | 'pending' | 'current';
}

export interface Medication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  status: 'on-track' | 'take-soon' | 'overdue';
}

export interface Insight {
  id: string;
  title: string;
  description: string;
  confidence: number;
  type: 'success' | 'info' | 'warning';
}

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'warning';
  action?: { label: string; onClick: () => void };
}

export interface WebSocketEvent {
  type: 'medication_added' | 'schedule_updated' | 'insight_generated' | 'chat_typing_start' | 'chat_message' | 'notification';
  payload: Record<string, unknown>;
}

export type Direction = 'ltr' | 'rtl';
export type Language = 'en' | 'ar';
