import { motion } from 'framer-motion';
import { fadeInUp, fadeInScale } from '@/lib/animations';
import { ScrollIndicator } from '@/components/ScrollIndicator';
import { useScrollTrigger } from '@/hooks/useScrollTrigger';

export function HeroSection() {
  const showScroll = !useScrollTrigger(100);

  return (
    <section className="relative min-h-screen bg-[#FFF7E6] overflow-hidden flex items-end pb-20">
      {/* Floating particles overlay */}
      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 30 }).map((_, i) => {
          const size = Math.random() * 1.5 + 0.5;
          const duration = 8 + Math.random() * 12;
          const xOffset = Math.random() * 200 - 100;
          const yOffset = Math.random() * 200 - 100;

          return (
            <motion.div
              key={i}
              className="absolute rounded-full bg-[#4D694E]"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                width: `${size}px`,
                height: `${size}px`,
                opacity: 0.15 + Math.random() * 0.4,
              }}
              animate={{
                x: [0, xOffset, 0],
                y: [0, yOffset, 0],
                opacity: [0.15, 0.5, 0.15],
              }}
              transition={{
                duration,
                repeat: Infinity,
                delay: Math.random() * 5,
                ease: 'easeInOut',
              }}
            />
          );
        })}
      </div>

      {/* Content */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex items-center gap-2 mb-6"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#6B8F6C] animate-pulse" />
          <span className="text-xs font-medium tracking-[0.2em] uppercase text-[#4D694E]">
            Healthcare AI Tracker
          </span>
        </motion.div>

        <motion.h1
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.8, delay: 0.4 }}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold text-gray-900 leading-[1.05] tracking-tight max-w-4xl"
        >
          The Intelligent
          <br />
          Core of
          <br />
          <span className="text-gradient-purple">Modern Healthcare.</span>
        </motion.h1>

        <motion.p
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.7, delay: 0.6 }}
          className="mt-6 text-base md:text-lg text-[rgba(0,0,0,0.6)] max-w-lg leading-relaxed"
        >
          A multi-agent orchestration layer designed for medical accuracy,
          long-term memory, and patient safety.
        </motion.p>

        <motion.div
          variants={fadeInScale}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.5, delay: 0.8 }}
          className="mt-8 flex items-center gap-4"
        >
          <span className="text-xs text-[rgba(0,0,0,0.4)] font-mono">v1.0.0</span>
          <span className="w-px h-4 bg-[rgba(0,0,0,0.1)]" />
          <span className="flex items-center gap-1.5 text-xs text-[#4D694E]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4D694E]" />
            System Active
          </span>
        </motion.div>
      </div>

      <ScrollIndicator visible={showScroll} />
    </section>
  );
}
