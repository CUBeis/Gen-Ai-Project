import { motion } from 'framer-motion';
import { GlassCard } from './GlassCard';

interface AgentFlowCardProps {
  step: number;
  name: string;
  role: string;
  description: string;
  position: 'left' | 'right';
  isRTL: boolean;
}

export function AgentFlowCard({ step, name, role, description, position, isRTL }: AgentFlowCardProps) {
  const isLeft = isRTL ? position === 'right' : position === 'left';

  return (
    <motion.div
      initial={{ x: isLeft ? -60 : 60, opacity: 0 }}
      whileInView={{ x: 0, opacity: 1 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ type: 'spring', stiffness: 300, damping: 30, delay: step * 0.1 }}
      className={`relative flex items-start gap-4 ${isLeft ? 'flex-row' : 'flex-row-reverse'} ${isLeft ? 'pr-8 md:pr-16' : 'pl-8 md:pl-16'}`}
      style={{ width: 'calc(50% - 20px)' }}
    >
      <div className="absolute top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-nerve-green flex items-center justify-center text-white text-sm font-bold z-10 shadow-lg"
        style={{ [isLeft ? 'right' : 'left']: '-60px' }}
      >
        {step}
      </div>
      <GlassCard variant="dark" className="w-full border border-[rgba(77,105,78,0.2)]">
        <h4 className="text-xl font-semibold text-[#FFF7E6] mb-1">{name}</h4>
        <p className="text-sm text-nerve-green-light mb-3 italic">&ldquo;{role}&rdquo;</p>
        <p className="text-sm text-[rgba(255,247,230,0.8)] leading-relaxed">{description}</p>
      </GlassCard>
    </motion.div>
  );
}
