import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { Message } from '@/types';

interface AnimatedMessageProps {
  message: Message;
  isRTL: boolean;
}

export function AnimatedMessage({ message, isRTL }: AnimatedMessageProps) {
  const isUser = message.sender === 'user';

  const formatContent = (content: string) => {
    const parts = content.split(/(\*\*.*?\*\*|\\n)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
      }
      if (part === '\n') {
        return <br key={i} />;
      }
      return part;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? (isRTL ? -30 : 30) : (isRTL ? 30 : -30), scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 400, damping: 35 }}
      className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
    >
      <div className={cn(
        'max-w-[75%]',
        isUser ? 'order-1' : 'order-1'
      )}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-2">
            <div className="w-5 h-5 rounded bg-nerve-green flex items-center justify-center">
              <div className="w-2.5 h-2.5 rounded-sm bg-white/80" />
            </div>
            <span className="text-xs font-semibold text-nerve-green">Nerve AI</span>
          </div>
        )}
        <div className={cn(
          'rounded-2xl px-5 py-3.5',
          isUser
            ? 'bg-nerve-green text-white rounded-tr-md shadow-[0_2px_8px_rgba(77,105,78,0.2)]'
            : 'bg-nerve-bg-secondary border border-[rgba(0,49,31,0.06)] shadow-[0_2px_12px_rgba(0,49,31,0.04)]'
        )}>
          <p className={cn(
            'text-[15px] leading-relaxed whitespace-pre-wrap',
            isUser ? 'text-white' : 'text-nerve-dark'
          )}>
            {formatContent(message.content)}
          </p>
        </div>
        <p className={cn(
          'text-[11px] mt-1.5',
          isUser ? 'text-right text-nerve-muted' : 'text-nerve-muted'
        )}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </motion.div>
  );
}
