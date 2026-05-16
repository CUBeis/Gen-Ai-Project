import { motion } from 'framer-motion';

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-7 h-7 rounded-lg bg-nerve-green/10 flex items-center justify-center">
        <div className="w-4 h-4 rounded bg-nerve-green" />
      </div>
      <div className="bg-nerve-bg-secondary rounded-2xl px-5 py-3.5 border border-[rgba(0,49,31,0.06)]">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-nerve-green"
              animate={{ y: [0, -6, 0] }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: i * 0.15,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
