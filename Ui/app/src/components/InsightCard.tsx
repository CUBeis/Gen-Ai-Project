import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { Insight } from '@/types';

const typeConfig = {
  success: { bg: 'bg-[rgba(34,197,94,0.06)]', border: 'border-l-green-500' },
  info: { bg: 'bg-[rgba(59,130,246,0.06)]', border: 'border-l-blue-500' },
  warning: { bg: 'bg-[rgba(245,158,11,0.06)]', border: 'border-l-amber-500' },
};

export function InsightCardComponent({ insight, isNew = false }: { insight: Insight; isNew?: boolean }) {
  const config = typeConfig[insight.type];

  return (
    <motion.div
      initial={isNew ? { opacity: 0, x: 50 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={cn(
        'p-3.5 rounded-xl border-l-[3px]',
        config.bg,
        config.border,
        isNew && 'ring-1 ring-nerve-blue/20'
      )}
    >
      <h4 className="text-sm font-semibold text-nerve-dark">{insight.title}</h4>
      <p className="text-xs text-nerve-muted mt-1 leading-relaxed">{insight.description}</p>
      <p className="text-[10px] text-nerve-muted mt-2 text-right">Confidence: {insight.confidence}%</p>
    </motion.div>
  );
}
