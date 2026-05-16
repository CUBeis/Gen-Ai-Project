import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Paperclip } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { useDirection } from '@/hooks/useDirection';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { AnimatedMessage } from '@/components/AnimatedMessage';
import { TypingIndicator } from '@/components/TypingIndicator';
import { QuickActionChip } from '@/components/QuickActionChip';
import { SkeletonLoader } from '@/components/SkeletonLoader';
import { TopBar } from './TopBar';
import { cn } from '@/lib/utils';
import { mockAIResponses, quickActions, welcomeMessage } from '@/data/mockData';

export function ChatInterface() {
  const { isRTL } = useDirection();
  const messages = useAppStore((s) => s.messages);
  const isTyping = useAppStore((s) => s.isTyping);
  const addMessage = useAppStore((s) => s.addMessage);
  const setTyping = useAppStore((s) => s.setTyping);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { ref: scrollRef } = useAutoScroll<HTMLDivElement>([messages.length, isTyping]);

  // Initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      if (messages.length === 0) {
        addMessage({ ...welcomeMessage, id: `welcome-${Date.now()}` });
      }
      setIsLoading(false);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  const simulateAIResponse = useCallback(
    (userContent: string) => {
      setTyping(true);
      const responseText = mockAIResponses[userContent] || mockAIResponses['default'];
      const delay = Math.min(800 + responseText.length * 12, 3000);

      setTimeout(() => {
        setTyping(false);
        addMessage({
          id: `ai-${Date.now()}`,
          sender: 'ai',
          content: responseText,
          timestamp: new Date(),
          type: 'text',
        });
      }, delay);
    },
    [addMessage, setTyping]
  );

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    // Add user message
    addMessage({
      id: `user-${Date.now()}`,
      sender: 'user',
      content: trimmed,
      timestamp: new Date(),
      type: 'text',
    });

    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.focus();
    }

    // Simulate AI response
    simulateAIResponse(trimmed);
  }, [inputValue, addMessage, simulateAIResponse]);

  const handleQuickAction = useCallback(
    (label: string) => {
      addMessage({
        id: `user-${Date.now()}`,
        sender: 'user',
        content: label,
        timestamp: new Date(),
        type: 'text',
      });
      simulateAIResponse(label);
    },
    [addMessage, simulateAIResponse]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const showQuickActions = messages.length === 1 && messages[0]?.sender === 'ai';

  return (
    <div className="flex flex-col h-screen bg-nerve-bg flex-1 min-w-0">
      <TopBar />

      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-thin p-4 md:p-6 space-y-4"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(0,49,31,0.03) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      >
        {isLoading ? (
          <div className="max-w-xl space-y-4">
            <div className="flex items-start gap-3">
              <SkeletonLoader type="avatar" className="w-12 h-12" />
              <div className="flex-1 pt-2">
                <SkeletonLoader lines={3} />
              </div>
            </div>
          </div>
        ) : (
          <>
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <AnimatedMessage key={msg.id} message={msg} isRTL={isRTL} />
              ))}
            </AnimatePresence>

            {/* Quick Actions */}
            <AnimatePresence>
              {showQuickActions && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ delay: 0.3 }}
                  className="flex flex-wrap gap-2 pl-8"
                >
                  {quickActions.map((action, i) => (
                    <motion.div
                      key={action.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.4 + i * 0.08 }}
                    >
                      <QuickActionChip
                        label={action.label}
                        icon={action.icon}
                        onClick={() => handleQuickAction(action.label)}
                      />
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Typing Indicator */}
            <AnimatePresence>
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <TypingIndicator />
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="shrink-0 bg-nerve-bg border-t border-[rgba(0,49,31,0.08)] p-4">
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <button className="w-10 h-10 rounded-xl flex items-center justify-center text-nerve-muted hover:text-nerve-green hover:bg-nerve-bg-secondary transition-all duration-200 shrink-0 mb-0.5">
            <Paperclip className="w-5 h-5" />
          </button>

          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your health, medications, or schedule..."
              rows={1}
              className={cn(
                'w-full px-4 py-3 rounded-xl bg-white border border-[rgba(0,49,31,0.12)]',
                'text-[15px] text-nerve-dark placeholder:text-nerve-muted resize-none',
                'focus:outline-none focus:border-nerve-green focus:ring-[3px] focus:ring-[rgba(77,105,78,0.15)]',
                'transition-all duration-200 max-h-[120px] scrollbar-thin'
              )}
            />
          </div>

          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 shrink-0 mb-0.5',
              inputValue.trim()
                ? 'bg-nerve-green text-white hover:bg-nerve-green-light hover:shadow-[0_2px_12px_rgba(77,105,78,0.3)]'
                : 'bg-nerve-bg-secondary text-nerve-muted opacity-40'
            )}
          >
            <Send className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
