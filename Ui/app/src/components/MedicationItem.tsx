import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Medication } from '@/types';

const statusConfig = {
  'on-track': { label: 'On Track', variant: 'default' as const, className: 'bg-green-500 hover:bg-green-500' },
  'take-soon': { label: 'Take Soon', variant: 'secondary' as const, className: 'bg-amber-500 hover:bg-amber-500 text-white' },
  'overdue': { label: 'Overdue', variant: 'destructive' as const, className: '' },
};

export function MedicationItemComponent({ medication, isNew = false }: { medication: Medication; isNew?: boolean }) {
  const config = statusConfig[medication.status];

  return (
    <motion.div
      initial={isNew ? { opacity: 0, y: -20, scale: 0.95 } : false}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={cn(
        'p-3 rounded-xl bg-[rgba(255,247,230,0.5)] hover:bg-[rgba(255,247,230,0.8)] transition-colors duration-200',
        isNew && 'ring-2 ring-nerve-green/30'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-nerve-dark">{medication.name}</p>
          <p className="text-xs text-nerve-muted mt-0.5">{medication.dosage} &middot; {medication.frequency}</p>
        </div>
        <Badge className={cn('text-[10px] font-semibold shrink-0', config.className)}>
          {config.label}
        </Badge>
      </div>
    </motion.div>
  );
}
