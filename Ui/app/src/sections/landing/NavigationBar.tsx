import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { fadeInDown } from '@/lib/animations';
import { useScrollTrigger } from '@/hooks/useScrollTrigger';
import { cn } from '@/lib/utils';

const navLinks = [
  { label: 'Agents', href: '#architecture' },
  { label: 'Intelligence', href: '#intelligence' },
  { label: 'Safety guard', href: '#agents' },
];

export function NavigationBar() {
  const scrolled = useScrollTrigger(50);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const handleNavClick = (href: string) => {
    setMobileOpen(false);
    const el = document.querySelector(href);
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <motion.nav
      variants={fadeInDown}
      initial="hidden"
      animate="visible"
      className={cn(
        'fixed top-0 left-0 right-0 z-50 h-[64px] flex items-center transition-all duration-300',
        scrolled
          ? 'bg-[rgba(255,247,230,0.85)] backdrop-blur-xl border-b border-[rgba(0,0,0,0.05)]'
          : 'bg-transparent'
      )}
    >
      <div className="w-full max-w-7xl mx-auto px-6 lg:px-12 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6B8F6C] to-[#4D694E] flex items-center justify-center">
            <span className="text-gray-900 text-sm font-bold">N</span>
          </div>
          <span className="text-base font-semibold text-gray-900 tracking-tight">Nerve AI</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <button
              key={link.label}
              onClick={() => handleNavClick(link.href)}
              className="text-sm font-medium text-[rgba(0,0,0,0.6)] hover:text-gray-900 transition-colors duration-200"
            >
              {link.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/app')}
            className="hidden sm:inline-flex items-center px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-[#6B8F6C] to-[#4D694E] text-gray-900 hover:opacity-90 transition-opacity duration-200 shadow-glow"
          >
            Request Access
          </button>
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2 text-gray-900">
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-full left-0 right-0 bg-[rgba(255,247,230,0.95)] backdrop-blur-xl border-b border-[rgba(0,0,0,0.05)] p-4 md:hidden"
        >
          {navLinks.map((link) => (
            <button
              key={link.label}
              onClick={() => handleNavClick(link.href)}
              className="block w-full text-left px-4 py-3 text-gray-900/80 font-medium hover:bg-black/5 rounded-lg"
            >
              {link.label}
            </button>
          ))}
        </motion.div>
      )}
    </motion.nav>
  );
}
