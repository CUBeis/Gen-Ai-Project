import { useState, useEffect, useRef } from 'react';

export function useTypingSimulator(fullText: string, isTyping: boolean, speedMs = 20) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const indexRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isTyping && fullText) {
      indexRef.current = 0;
      setDisplayedText('');
      setIsComplete(false);

      intervalRef.current = setInterval(() => {
        indexRef.current += 1;
        if (indexRef.current >= fullText.length) {
          setDisplayedText(fullText);
          setIsComplete(true);
          if (intervalRef.current) clearInterval(intervalRef.current);
        } else {
          setDisplayedText(fullText.slice(0, indexRef.current));
        }
      }, speedMs);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isTyping, fullText, speedMs]);

  return { displayedText, isComplete };
}
