import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  MessageSquare,
  HeartPulse,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { slideInLeft } from '@/lib/animations';
import { useSidebar } from '@/hooks/useSidebar';
import { NavLink } from '@/components/NavLink';
import { cn } from '@/lib/utils';
import { useState } from 'react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard' },
  { icon: MessageSquare, label: 'Chat' },
  { icon: HeartPulse, label: 'Care Plan' },
  { icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const { collapsed, toggleSidebar } = useSidebar();
  const [activeItem, setActiveItem] = useState('Chat');

  return (
    <motion.aside
      variants={slideInLeft}
      initial="hidden"
      animate="visible"
      className={cn(
        'h-screen bg-nerve-bg-secondary border-r border-[rgba(0,49,31,0.06)] flex flex-col shrink-0 transition-all duration-350 z-40',
        collapsed ? 'w-[72px]' : 'w-[260px]'
      )}
      style={{ transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)' }}
    >
      {/* Logo Area */}
      <div className="p-4 pb-5 border-b border-[rgba(0,49,31,0.06)]">
        <div className={cn('flex items-center', collapsed ? 'justify-center' : 'gap-3')}>
          <div className="w-9 h-9 rounded-lg bg-nerve-green flex items-center justify-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-white">
              <path d="M12 2L20.66 7V17L12 22L3.34 17V7L12 2Z" stroke="currentColor" strokeWidth="2" fill="none"/>
              <circle cx="12" cy="12" r="3" fill="currentColor"/>
            </svg>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="text-lg font-bold text-nerve-dark whitespace-nowrap overflow-hidden"
              >
                Nerve AI
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            icon={item.icon}
            label={item.label}
            active={activeItem === item.label}
            collapsed={collapsed}
            onClick={() => setActiveItem(item.label)}
          />
        ))}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-[rgba(0,49,31,0.06)]">
        <button
          onClick={toggleSidebar}
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center text-nerve-muted hover:bg-[rgba(77,105,78,0.1)] hover:text-nerve-green transition-all duration-200',
            collapsed ? 'mx-auto' : 'ml-auto'
          )}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* User Profile */}
      <div className="p-3 border-t border-[rgba(0,49,31,0.06)]">
        <div className={cn(
          'flex items-center gap-3 p-2.5 rounded-xl bg-[rgba(77,105,78,0.06)]',
          collapsed && 'justify-center'
        )}>
          <div className="w-9 h-9 rounded-full bg-nerve-green flex items-center justify-center text-white text-sm font-semibold shrink-0">
            N
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="overflow-hidden"
              >
                <p className="text-sm font-semibold text-nerve-dark truncate">NUNO</p>
                <p className="text-[11px] text-nerve-muted">Active Patient</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.aside>
  );
}
