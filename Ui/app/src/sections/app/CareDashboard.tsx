import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-nerve-dark">Today's Care</h3>
                <span className="text-[11px] text-nerve-muted">{schedule.length} tasks</span>
              </div>
              <div className="space-y-2.5">
                {schedule.slice(0, 4).map((item) => (
                  <ScheduleItemComponent key={item.id} item={item} />
                ))}
              </div>
            </motion.div>

            <motion.div variants={fadeInUp} className="glass rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-nerve-dark">Medications</h3>
                <span className="text-[11px] text-nerve-muted">{medications.length} active</span>
              </div>
              <div className="space-y-3">
                {medications.slice(0, 3).map((medication) => (
                  <MedicationItemComponent key={medication.id} medication={medication} />
                ))}
              </div>
            </motion.div>

            <motion.div variants={fadeInUp} className="glass rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-nerve-dark">Insights</h3>
                <span className="text-[11px] text-nerve-muted">{insights.length} live</span>
              </div>
              <div className="space-y-3">
                {insights.slice(0, 2).map((insight) => (
                  <InsightCardComponent key={insight.id} insight={insight} />
                ))}
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
