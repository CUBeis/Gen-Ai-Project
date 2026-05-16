import { motion } from 'framer-motion';
import { useMemo } from 'react';

interface Halo {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  xOffset: number;
  yOffset: number;
}

interface Thread {
  id: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  duration: number;
}

export function AnimatedHalosAndThreads() {
  const halos = useMemo<Halo[]>(() =>
    Array.from({ length: 8 }).map((_, i) => ({
      id: i,
      x: Math.random() * 80 + 10,
      y: Math.random() * 80 + 10,
      size: Math.random() * 200 + 100,
      duration: 15 + Math.random() * 10,
      xOffset: Math.random() * 150 - 75,
      yOffset: Math.random() * 150 - 75,
    })),
    []
  );

  const threads = useMemo<Thread[]>(() =>
    Array.from({ length: 6 }).map((_, i) => {
      const startHalo = halos[i % halos.length];
      const endHalo = halos[(i + 1) % halos.length];
      return {
        id: i,
        x1: startHalo.x,
        y1: startHalo.y,
        x2: endHalo.x,
        y2: endHalo.y,
        duration: 20 + Math.random() * 10,
      };
    }),
    [halos]
  );

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {/* SVG Layer for Threads */}
      <svg
        className="absolute inset-0 w-full h-full"
        style={{ background: 'transparent' }}
        preserveAspectRatio="none"
      >
        <defs>
          <filter id="threadGlow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {threads.map((thread) => (
          <motion.line
            key={`thread-${thread.id}`}
            x1={`${thread.x1}%`}
            y1={`${thread.y1}%`}
            x2={`${thread.x2}%`}
            y2={`${thread.y2}%`}
            stroke="#EF4444"
            strokeWidth="2"
            strokeOpacity="0.4"
            filter="url(#threadGlow)"
            animate={{
              strokeOpacity: [0.2, 0.6, 0.2],
            }}
            transition={{
              duration: thread.duration,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}
      </svg>

      {/* Halos */}
      {halos.map((halo) => (
        <motion.div
          key={`halo-${halo.id}`}
          className="absolute rounded-full border-2 border-green-400"
          style={{
            left: `${halo.x}%`,
            top: `${halo.y}%`,
            width: `${halo.size}px`,
            height: `${halo.size}px`,
            transform: 'translate(-50%, -50%)',
            boxShadow: '0 0 30px rgba(74, 222, 128, 0.4), inset 0 0 30px rgba(74, 222, 128, 0.2)',
          }}
          animate={{
            x: halo.xOffset,
            y: halo.yOffset,
            opacity: [0.3, 0.6, 0.3],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: halo.duration,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: Math.random() * 3,
          }}
        />
      ))}
    </div>
  );
}
