import { motion } from 'framer-motion';
import { Shield, Eye, Filter, Activity, Lock } from 'lucide-react';
import { fadeInUp, staggerContainer, fadeInScale } from '@/lib/animations';

const safeguards = [
  { icon: Shield, label: 'Prompt Injection Shield' },
  { icon: Eye, label: 'Full Observability' },
  { icon: Filter, label: 'Output Filtering' },
  { icon: Activity, label: 'Real-Time Tracing' },
];

export function SafetySection() {
  return (
    <section id="agents" className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(244,63,94,0.2)] to-transparent" />

      <div className="max-w-4xl mx-auto px-6 text-center">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f43f5e]" />
            <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#f43f5e]">Safety</span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900">
            Guardrails at Every
            <br />
            <span className="bg-gradient-to-r from-[#f43f5e] to-[#f97316] bg-clip-text text-transparent">Layer</span>
          </h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mt-14 flex flex-wrap justify-center gap-4"
        >
          {safeguards.map((s) => (
            <motion.div
              key={s.label}
              variants={fadeInScale}
              whileHover={{ y: -4, scale: 1.05 }}
              className="flex flex-col items-center gap-3 px-6 py-5 rounded-xl bg-[rgba(0,0,0,0.02)] border border-[rgba(0,0,0,0.06)] hover:border-[#e06666] hover:shadow-[0_0_16px_rgba(224,102,102,0.3)] transition-all min-w-[140px]"
            >
              <s.icon className="w-6 h-6 text-[rgba(0,0,0,0.5)]" />
              <span className="text-xs font-medium text-[rgba(0,0,0,0.6)]">{s.label}</span>
            </motion.div>
          ))}
        </motion.div>

        {/* Central shield */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-10"
        >
          <div className="inline-flex items-center gap-3 px-5 py-3 rounded-full bg-[rgba(244,63,94,0.08)] border border-[rgba(244,63,94,0.2)]">
            <Lock className="w-4 h-4 text-[#f43f5e]" />
            <span className="text-sm font-medium text-[#f43f5e]">HIPAA-Ready Storage</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
