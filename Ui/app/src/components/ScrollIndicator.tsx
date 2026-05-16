import { motion } from 'framer-motion';

export function ScrollIndicator({ visible }: { visible: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.5 }}
      className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
    >
      <div className="relative w-0.5 h-10 bg-[rgba(255,247,230,0.3)] rounded-full overflow-hidden">
        <motion.div
          className="absolute w-full h-3 bg-[rgba(255,247,230,0.6)] rounded-full"
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
    </motion.div>
  );
}
