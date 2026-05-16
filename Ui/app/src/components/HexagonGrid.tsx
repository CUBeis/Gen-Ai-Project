import { memo } from 'react';

const HexagonGrid = memo(function HexagonGrid({ className }: { className?: string }) {
  const hexSize = 60;

  return (
    <svg
      className={className}
      width="100%"
      height="100%"
      style={{ animation: 'spin 60s linear infinite' }}
    >
      <defs>
        <pattern
          id="hexagon"
          width={hexSize * 2}
          height={hexSize * Math.sqrt(3)}
          patternUnits="userSpaceOnUse"
          patternTransform="scale(0.5)"
        >
          <polygon
            points={`${hexSize},0 ${hexSize * 1.5},${hexSize * 0.43} ${hexSize * 1.5},${hexSize * 1.3} ${hexSize},${hexSize * 1.73} ${hexSize * 0.5},${hexSize * 1.3} ${hexSize * 0.5},${hexSize * 0.43}`}
            fill="none"
            stroke="rgba(77, 105, 78, 0.12)"
            strokeWidth="1"
          />
          <polygon
            points={`${hexSize * 2},${hexSize * 0.87} ${hexSize * 2.5},${hexSize * 1.3} ${hexSize * 2.5},${hexSize * 2.17} ${hexSize * 2},${hexSize * 2.6} ${hexSize * 1.5},${hexSize * 2.17} ${hexSize * 1.5},${hexSize * 1.3}`}
            fill="none"
            stroke="rgba(77, 105, 78, 0.12)"
            strokeWidth="1"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#hexagon)" />
    </svg>
  );
});

export { HexagonGrid };
