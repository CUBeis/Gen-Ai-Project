import { motion } from 'framer-motion';
import { fadeInUp } from '@/lib/animations';
import { Github } from 'lucide-react';

const links = [
  { label: 'Agents', href: '#architecture' },
  { label: 'Intelligence', href: '#intelligence' },
  { label: 'Safety guard', href: '#agents' },
];

export function FooterSection() {
  const handleClick = (href: string) => {
    const el = document.querySelector(href);
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <footer className="bg-[#FFF7E6] border-t border-[rgba(0,0,0,0.05)]">
      <motion.div
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="max-w-6xl mx-auto px-6 py-10"
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-[#6B8F6C] to-[#4D694E] flex items-center justify-center">
              <span className="text-gray-900 text-xs font-bold">N</span>
            </div>
            <span className="text-sm font-semibold text-gray-900">Nerve AI</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 md:gap-8">
            {links.map((link) => (
              <button
                key={link.label}
                onClick={() => handleClick(link.href)}
                className="text-sm text-[rgba(0,0,0,0.5)] hover:text-gray-900 transition-colors"
              >
                {link.label}
              </button>
            ))}
            <a href="#" className="text-sm text-[rgba(0,0,0,0.5)] hover:text-gray-900 transition-colors flex items-center gap-1.5">
              <Github className="w-4 h-4" />
              GitHub
            </a>
          </div>
        </div>

        <div className="mt-4 text-center">
          <span className="inline-flex items-center gap-1.5 text-[10px] text-[#6B8F6C]">
            <span className="w-1 h-1 rounded-full bg-[#6B8F6C] animate-pulse" />
            2026 Nerve AI. All rights reserved.
          </span>
        </div>
      </motion.div>
    </footer>
  );
}
