import { memo } from 'react';

const GlowOrbs = memo(function GlowOrbs({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div
        className="absolute w-[400px] h-[400px] rounded-full animate-float-slow"
        style={{
          background: 'radial-gradient(circle, rgba(37, 99, 235, 0.12) 0%, transparent 70%)',
          top: '10%',
          left: '5%',
        }}
      />
      <div
        className="absolute w-[500px] h-[500px] rounded-full animate-float-slow"
        style={{
          background: 'radial-gradient(circle, rgba(77, 105, 78, 0.15) 0%, transparent 70%)',
          bottom: '10%',
          right: '5%',
          animationDelay: '-10s',
        }}
      />
    </div>
  );
});

export { GlowOrbs };
