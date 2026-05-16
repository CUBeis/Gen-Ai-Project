import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { fadeInUp } from '@/lib/animations';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  index?: number;
}

export function FeatureCard({ icon: Icon, title, description }: FeatureCardProps) {
  return (
    <motion.div
      variants={fadeInUp}
      whileHover={{ y: -4, boxShadow: '0 12px 40px rgba(0, 49, 31, 0.12)' }}
      transition={{ duration: 0.3 }}
      className="relative bg-white rounded-2xl p-8 shadow-elevated border border-[rgba(0,49,31,0.06)] overflow-hidden group cursor-default"
    >
      <div className="absolute top-0 left-8 w-10 h-[3px] bg-nerve-green rounded-b-full transition-all duration-400 group-hover:w-[calc(100%-64px)]" />
      <div className="w-14 h-14 rounded-xl bg-nerve-green/10 flex items-center justify-center mb-5">
        <Icon className="w-7 h-7 text-nerve-green" />
      </div>
      <h3 className="text-2xl font-semibold text-nerve-dark mb-3">{title}</h3>
      <p className="text-base text-nerve-muted leading-relaxed">{description}</p>
    </motion.div>
  );
}
