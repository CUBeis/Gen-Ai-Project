import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface NeonButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function NeonButton({ children, onClick, className, size = 'md' }: NeonButtonProps) {
  const sizeClasses = {
    sm: 'px-5 py-2.5 text-sm',
    md: 'px-8 py-3.5 text-base',
    lg: 'px-9 py-4 text-lg',
  };

  return (
    <motion.div
      animate={{
        boxShadow: [
          '0 0 10px rgba(37, 99, 235, 0.3)',
          '0 0 25px rgba(37, 99, 235, 0.5)',
          '0 0 10px rgba(37, 99, 235, 0.3)',
        ],
      }}
      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      className="rounded-xl inline-block"
    >
      <Button
        onClick={onClick}
        className={cn(
          'bg-[#00311F] text-white border border-[#2563EB]/50 hover:bg-[#0A4F37] hover:border-[#2563EB] font-semibold rounded-xl transition-all duration-300',
          sizeClasses[size],
          className
        )}
      >
        {children}
      </Button>
    </motion.div>
  );
}
