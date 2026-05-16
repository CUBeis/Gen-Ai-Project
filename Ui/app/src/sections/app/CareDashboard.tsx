import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  Pill,
  Sparkles,
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { slideInRight, staggerContainer, fadeInUp } from '@/lib/animations';
import { ScheduleItemComponent } from '@/components/ScheduleItem';
import { MedicationItemComponent } from '@/components/MedicationItem';
import { InsightCardComponent } from '@/components/InsightCard';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { SkeletonLoader } from '@/components/SkeletonLoader';
import { initialSchedule, initialMedications, initialInsights } from '@/data/mockData';

export function CareDashboard() {
  const schedule = useAppStore((s) => s.schedule);
  const medications = useAppStore((s) => s.medications);
  const insights = useAppStore((s) => s.insights);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const addScheduleItem = useAppStore((s) => s.addScheduleItem);
  const addMedication = useAppStore((s) => s.addMedication);
  const addInsight = useAppStore((s) => s.addInsight);
  const [isLoading, setIsLoading] = useState(true);
  const [newMedId, setNewMedId] = useState<string | null>(null);
  const [newInsightId, setNewInsightId] = useState<string | null>(null);

  // Track new items for animation
  const prevMedsLength = useRef(medications.length);
  const prevInsightsLength = useRef(insights.length);

  // Initialize data
  useEffect(() => {
    const timer = setTimeout(() => {
      if (schedule.length === 0) {
        initialSchedule.forEach(addScheduleItem);
      }
      if (medications.length === 0) {
        initialMedications.forEach(addMedication);
      }
      if (insights.length === 0) {
        initialInsights.forEach(addInsight);
      }
      setIsLoading(false);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  // Track new items
  useEffect(() => {
    if (medications.length > prevMedsLength.current) {
      setNewMedId(medications[0]?.id || null);
      setTimeout(() => setNewMedId(null), 3000);
    }
    prevMedsLength.current = medications.length;
  }, [medications.length]);

  useEffect(() => {
    if (insights.length > prevInsightsLength.current) {
      setNewInsightId(insights[0]?.id || null);
      setTimeout(() => setNewInsightId(null), 3000);
    }
    prevInsightsLength.current = insights.length;
  }, [insights.length]);

  const completedCount = schedule.filter((s) => s.status === 'completed').length;
  const activeMedications = medications.filter(
    (m) => m.status === 'on-track' || m.status === 'take-soon'
  ).length;

  return (
    <motion.aside
      variants={slideInRight}
      initial="hidden"
      animate="visible"
      className="w-[380px] h-screen bg-nerve-bg-secondary border-l border-[rgba(0,49,31,0.06)] flex flex-col shrink-0 overflow-hidden"
    >

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-5">
        {isLoading ? (
          <>
            <SkeletonLoader type="card" lines={4} />
            <SkeletonLoader type="card" lines={3} />
            <SkeletonLoader type="card" lines={2} />
          </>
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="space-y-5"
          >
            {/* Health Insights */}
            <motion.div variants={fadeInUp} className="glass rounded-2xl p-5">
              <div className="space-y-2.5">
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>

      {/* Connection Status */}
      <div className="p-4 border-t border-[rgba(0,49,31,0.06)]">
        <ConnectionStatus connected={wsConnected} />
      </div>
    </motion.aside>
  );
}

