import { motion } from 'framer-motion';
import { fadeInUp, staggerContainer } from '@/lib/animations';
import { cn } from '@/lib/utils';

const agents = [
  {
    num: '01',
    name: 'Router',
    subtitle: 'Intent Classification',
    description: 'Classifies patient intent and dynamically routes queries to the appropriate specialized agent.',
    color: 'from-cyan-500/20 to-blue-500/20',
    border: 'border-cyan-500/20',
    glow: 'shadow-[0_0_20px_rgba(6,182,212,0.1)]',
  },
  {
    num: '02',
    name: 'Profiler',
    subtitle: 'Onboarding',
    description: 'Collects patient profiles, medical history, and stores structured data for long-term memory.',
    color: 'from-purple-500/20 to-pink-500/20',
    border: 'border-purple-500/20',
    glow: 'shadow-[0_0_20px_rgba(77, 105, 78,0.1)]',
  },
  {
    num: '03',
    name: 'Care Planner',
    subtitle: 'Treatment Tracking',
    description: 'Manages medication schedules, care plans, and generates treatment timelines.',
    color: 'from-emerald-500/20 to-teal-500/20',
    border: 'border-emerald-500/20',
    glow: 'shadow-[0_0_20px_rgba(16,185,129,0.1)]',
  },
  {
    num: '04',
    name: 'Clinical RAG',
    subtitle: 'Medical Retrieval',
    description: 'Retrieves relevant clinical knowledge from vector databases to augment LLM responses.',
    color: 'from-amber-500/20 to-orange-500/20',
    border: 'border-amber-500/20',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.1)]',
  },
  {
    num: '05',
    name: 'Guardrail',
    subtitle: 'Safety Filter',
    description: 'Monitors all outputs for safety, filtering harmful or incorrect medical information.',
    color: 'from-rose-500/20 to-red-500/20',
    border: 'border-rose-500/20',
    glow: 'shadow-[0_0_20px_rgba(244,63,94,0.1)]',
  },
];

function AgentCard({ agent }: { agent: (typeof agents)[0] }) {
  return (
    <motion.div
      variants={fadeInUp}
      whileHover={{ y: -6, scale: 1.02 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'relative rounded-2xl p-6 bg-gradient-to-b border group cursor-default overflow-hidden',
        agent.color,
        agent.border,
        agent.glow
      )}
    >
      <div className="relative z-10">
        <span className="text-xs font-mono text-[rgba(0,0,0,0.3)]">{agent.num}</span>
        <div className="mt-4 mb-2">
          <div className="w-12 h-12 rounded-xl bg-[rgba(0,0,0,0.05)] border border-[rgba(0,0,0,0.08)] flex items-center justify-center mb-4 group-hover:bg-[rgba(0,0,0,0.08)] transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-gray-900/60">
              <path d="M12 2L20.66 7V17L12 22L3.34 17V7L12 2Z" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="2" fill="currentColor" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
          <p className="text-xs text-[#6B8F6C] font-medium mt-0.5">{agent.subtitle}</p>
        </div>
        <p className="text-sm text-[rgba(0,0,0,0.5)] leading-relaxed">{agent.description}</p>
      </div>
    </motion.div>
  );
}

export function ArchitectureSection() {
  return (
    <section id="architecture" className="bg-[#FFF7E6] py-24 md:py-32 relative">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mb-16"
        >
          <div className="flex items-center gap-2 mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4D694E]" />
            <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#4D694E]">
              Architecture
            </span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 max-w-xl leading-tight">
            Built as a{' '}
            <span className="text-gradient-purple">Living System</span>
          </h2>
          <p className="mt-4 text-[rgba(0,0,0,0.5)] max-w-lg leading-relaxed">
            Five specialized agents work in concert — each with a dedicated role in the
            patient journey, from initial intake to clinical retrieval and safety guardrails.
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
        >
          {agents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </motion.div>

        {/* Agent network image */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="mt-16 rounded-2xl overflow-hidden border border-[rgba(0,0,0,0.05)]"
        >
          <img
            src="./images/Built as a Living System.png"
            alt="Multi-agent orchestration system"
            className="w-full h-auto opacity-80"
          />
        </motion.div>
      </div>
    </section>
  );
}
