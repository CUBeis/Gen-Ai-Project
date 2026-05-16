import { useEffect } from 'react';
import { Bell, Calendar, Lock, Pill, Settings, ShieldCheck, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAppStore } from '@/store/useAppStore';
import { Sidebar } from '@/sections/app/Sidebar';
import { ChatInterface } from '@/sections/app/ChatInterface';
import { CareDashboard } from '@/sections/app/CareDashboard';
import { ToastContainer } from '@/components/ToastNotification';
import { ScheduleItemComponent } from '@/components/ScheduleItem';
import { MedicationItemComponent } from '@/components/MedicationItem';
import { InsightCardComponent } from '@/components/InsightCard';
import { initialSchedule, initialMedications, initialInsights } from '@/data/mockData';
import { cn } from '@/lib/utils';

function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="h-[72px] bg-nerve-bg/80 backdrop-blur-lg border-b border-[rgba(0,49,31,0.06)] flex items-center justify-between px-6 shrink-0">
      <div>
        <h2 className="text-xl font-semibold text-nerve-dark">{title}</h2>
        <p className="text-xs text-nerve-muted mt-0.5">{subtitle}</p>
      </div>
    </header>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-4">
      <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center mb-3', tone)}>
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-xs text-nerve-muted">{label}</p>
      <p className="text-2xl font-semibold text-nerve-dark mt-1">{value}</p>
    </div>
  );
}

function DashboardView() {
  const schedule = useAppStore((s) => s.schedule.length ? s.schedule : initialSchedule);
  const medications = useAppStore((s) => s.medications.length ? s.medications : initialMedications);
  const insights = useAppStore((s) => s.insights.length ? s.insights : initialInsights);
  const completed = schedule.filter((item) => item.status === 'completed').length;

  return (
    <section className="flex flex-col h-screen bg-nerve-bg flex-1 min-w-0">
      <PanelHeader title="Dashboard" subtitle="A quick view of today's care activity and AI insights" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard icon={Calendar} label="Tasks completed" value={`${completed}/${schedule.length}`} tone="bg-green-50 text-green-600" />
          <StatCard icon={Pill} label="Active medications" value={`${medications.length}`} tone="bg-amber-50 text-amber-600" />
          <StatCard icon={TrendingUp} label="Latest insights" value={`${insights.length}`} tone="bg-blue-50 text-blue-600" />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <div className="rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-5">
            <h3 className="text-sm font-semibold text-nerve-dark mb-3">Today's Schedule</h3>
            <div className="space-y-1">
              {schedule.map((item) => <ScheduleItemComponent key={item.id} item={item} />)}
            </div>
          </div>

          <div className="rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-5">
            <h3 className="text-sm font-semibold text-nerve-dark mb-3">AI Insights</h3>
            <div className="space-y-3">
              {insights.map((insight) => <InsightCardComponent key={insight.id} insight={insight} />)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CarePlanView() {
  const schedule = useAppStore((s) => s.schedule.length ? s.schedule : initialSchedule);
  const medications = useAppStore((s) => s.medications.length ? s.medications : initialMedications);

  return (
    <section className="flex flex-col h-screen bg-nerve-bg flex-1 min-w-0">
      <PanelHeader title="Care Plan" subtitle="Medication and schedule items the assistant can help update" />
      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 xl:grid-cols-2 gap-5 content-start">
        <div className="rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-5">
          <h3 className="text-sm font-semibold text-nerve-dark mb-3">Medications</h3>
          <div className="space-y-3">
            {medications.map((medication) => <MedicationItemComponent key={medication.id} medication={medication} />)}
          </div>
        </div>
        <div className="rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-5">
          <h3 className="text-sm font-semibold text-nerve-dark mb-3">Schedule</h3>
          <div className="space-y-1">
            {schedule.map((item) => <ScheduleItemComponent key={item.id} item={item} />)}
          </div>
        </div>
      </div>
    </section>
  );
}

function SettingsView() {
  const language = useAppStore((s) => s.language);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const setActiveView = useAppStore((s) => s.setActiveView);

  return (
    <section className="flex flex-col h-screen bg-nerve-bg flex-1 min-w-0">
      <PanelHeader title="Settings" subtitle="Local demo settings and connection state" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl rounded-xl bg-white border border-[rgba(0,49,31,0.08)] p-5 space-y-4">
          <div className="flex items-center justify-between gap-4 py-3 border-b border-[rgba(0,49,31,0.06)]">
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-nerve-green" />
              <div>
                <p className="text-sm font-semibold text-nerve-dark">Language</p>
                <p className="text-xs text-nerve-muted">Current app language mode</p>
              </div>
            </div>
            <span className="text-sm font-medium text-nerve-dark uppercase">{language}</span>
          </div>

          <div className="flex items-center justify-between gap-4 py-3 border-b border-[rgba(0,49,31,0.06)]">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-nerve-green" />
              <div>
                <p className="text-sm font-semibold text-nerve-dark">Realtime updates</p>
                <p className="text-xs text-nerve-muted">Demo notification stream</p>
              </div>
            </div>
            <span className={cn('text-sm font-medium', wsConnected ? 'text-green-600' : 'text-amber-600')}>
              {wsConnected ? 'Connected' : 'Offline'}
            </span>
          </div>

          <div className="flex items-start gap-3 rounded-lg bg-[rgba(77,105,78,0.06)] p-4">
            <ShieldCheck className="w-5 h-5 text-nerve-green mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-nerve-dark">Demo mode</p>
              <p className="text-xs text-nerve-muted mt-1 leading-relaxed">
                Chat uses the local backend demo endpoint while PostgreSQL auth is not running.
              </p>
            </div>
          </div>

          <button
            onClick={() => setActiveView('Chat')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-nerve-green text-white text-sm font-semibold hover:bg-nerve-green-light transition-colors"
          >
            <Lock className="w-4 h-4" />
            Back to chat
          </button>
        </div>
      </div>
    </section>
  );
}

export default function MainApp() {
  useWebSocket(true);
  const activeView = useAppStore((s) => s.activeView);

  useEffect(() => {
    // Ensure scroll is at top
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-nerve-bg">
      <ToastContainer />
      <Sidebar />
      {activeView === 'Chat' && (
        <>
          <ChatInterface />
          <CareDashboard />
        </>
      )}
      {activeView === 'Dashboard' && <DashboardView />}
      {activeView === 'Care Plan' && <CarePlanView />}
      {activeView === 'Settings' && <SettingsView />}
    </div>
  );
}
