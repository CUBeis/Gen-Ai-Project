import type { ScheduleItem, Medication, Insight, Message } from '@/types';

export const initialSchedule: ScheduleItem[] = [
  { id: 's1', time: '08:00 AM', title: 'Morning Medication', icon: 'pill', status: 'completed' },
  { id: 's2', time: '09:30 AM', title: 'Blood Pressure Check', icon: 'activity', status: 'current' },
  { id: 's3', time: '12:00 PM', title: 'Lunch + Metformin', icon: 'pill', status: 'upcoming' },
  { id: 's4', time: '03:00 PM', title: 'Walk (30 min)', icon: 'trending-up', status: 'upcoming' },
  { id: 's5', time: '09:00 PM', title: 'Evening Medication', icon: 'pill', status: 'pending' },
];

export const initialMedications: Medication[] = [
  { id: 'm1', name: 'Metformin', dosage: '500mg', frequency: 'Twice daily', status: 'on-track' },
  { id: 'm2', name: 'Lisinopril', dosage: '10mg', frequency: 'Once daily (morning)', status: 'on-track' },
  { id: 'm3', name: 'Atorvastatin', dosage: '20mg', frequency: 'Once daily (evening)', status: 'take-soon' },
];

export const initialInsights: Insight[] = [
  {
    id: 'i1',
    title: 'Blood Pressure Trend',
    description: 'Your BP readings have been stable for 14 days. Keep up the good work!',
    confidence: 94,
    type: 'success',
  },
  {
    id: 'i2',
    title: 'Activity Goal',
    description: "You're 70% toward your weekly walking goal. 3 more sessions needed.",
    confidence: 88,
    type: 'info',
  },
  {
    id: 'i3',
    title: 'Medication Adherence',
    description: "You've taken 98% of prescribed doses this month. Excellent adherence!",
    confidence: 99,
    type: 'success',
  },
];

export const welcomeMessage: Message = {
  id: 'welcome',
  sender: 'ai',
  content: "Hello! I'm your Nerve AI care companion. I can help you track medications, answer health questions, create care schedules, and provide personalized wellness insights. What would you like to talk about today?",
  timestamp: new Date(),
  type: 'text',
};

export const quickActions = [
  { id: 'qa1', label: 'My Medications', icon: 'pill' },
  { id: 'qa2', label: "Today's Schedule", icon: 'calendar' },
  { id: 'qa3', label: 'Health Insights', icon: 'sparkles' },
  { id: 'qa4', label: 'New Symptom', icon: 'alert-circle' },
];

export const mockAIResponses: Record<string, string> = {
  'My Medications':
    "Here are your current medications:\n\n**Metformin** — 500mg, twice daily\n**Lisinopril** — 10mg, once daily in the morning\n**Atorvastatin** — 20mg, once daily in the evening\n\nYou're doing great with adherence at 98% this month! Your next dose is Lisinopril at 8:00 AM tomorrow.",
  "Today's Schedule":
    "Here's your schedule for today:\n\n- **08:00 AM** — Morning Medication (completed)\n- **09:30 AM** — Blood Pressure Check (current)\n- **12:00 PM** — Lunch + Metformin\n- **03:00 PM** — Walk (30 minutes)\n- **09:00 PM** — Evening Medication\n\nYou've completed 1 of 5 tasks. Great start!",
  'Health Insights':
    "Your latest health insights:\n\n**Blood Pressure Trend** — Stable for 14 days (94% confidence)\n**Activity Goal** — 70% toward weekly walking goal (88% confidence)\n**Medication Adherence** — 98% this month (99% confidence)\n\nOverall, your health metrics are looking positive. Keep maintaining your routine!",
  'New Symptom':
    "I'm sorry to hear you're experiencing a new symptom. To help you best, could you tell me:\n\n1. What symptom are you experiencing?\n2. When did it start?\n3. How severe is it on a scale of 1-10?\n4. Any other symptoms accompanying it?\n\nThis information will help me provide better guidance and determine if you should consult your doctor.",
  default:
    "Thank you for sharing that with me. Based on your health profile, I recommend monitoring this closely and keeping track of any changes. Would you like me to add a reminder to your care schedule or provide more specific information about this topic?",
};

export const randomMedications: Medication[] = [
  { id: 'rm1', name: 'Vitamin D3', dosage: '2000 IU', frequency: 'Once daily', status: 'on-track' },
  { id: 'rm2', name: 'Omega-3', dosage: '1000mg', frequency: 'Once daily', status: 'on-track' },
  { id: 'rm3', name: 'Aspirin', dosage: '81mg', frequency: 'Once daily', status: 'take-soon' },
];

export const randomInsights: Insight[] = [
  {
    id: 'ri1',
    title: 'Sleep Pattern',
    description: 'Your average sleep duration improved by 30 minutes this week. Aim for 7-8 hours consistently.',
    confidence: 85,
    type: 'info',
  },
  {
    id: 'ri2',
    title: 'Hydration Reminder',
    description: "You've been below your daily water intake goal for 2 days. Try to drink 8 glasses today.",
    confidence: 78,
    type: 'warning',
  },
  {
    id: 'ri3',
    title: 'Weight Trend',
    description: 'Your weight has been stable within a healthy range for the past month. Keep up the balanced diet!',
    confidence: 92,
    type: 'success',
  },
];
