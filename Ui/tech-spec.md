# Nerve AI — Technical Specification

## 1. Development Environment

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 15.x |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | 3.x |
| UI Components | shadcn/ui | latest |
| Animation | Framer Motion | 11.x |
| Icons | Lucide React | latest |
| State Management | Zustand | 4.x |

---

## 2. Dependencies

### Core (pre-installed with shadcn init)

| Package | Purpose |
|---------|---------|
| `next` | Framework, App Router, file-based routing |
| `react` / `react-dom` | UI library |
| `typescript` | Type safety |
| `tailwindcss` / `postcss` / `autoprefixer` | Utility-first CSS |
| `tailwind-merge` | Merge Tailwind classes without conflicts |
| `clsx` / `class-variance-authority` | Conditional class composition (shadcn pattern) |
| `lucide-react` | Icon library — all icons from design.md |
| `framer-motion` | Declarative animations, AnimatePresence, gestures |
| `@radix-ui/*` | Accessible UI primitives (via shadcn components) |

### Additional Required

| Package | Purpose |
|---------|---------|
| `zustand` | Lightweight global state (RTL direction, sidebar collapse, language) |

### Fonts (loaded via `next/font/google`)

| Font | Weights | Usage |
|------|---------|-------|
| `Inter` | 300, 400, 500, 600, 700 | Primary Latin typography |
| `Noto Sans Arabic` | 400, 500, 600, 700 | Arabic/RTL text |

`JetBrains Mono` is **not** needed — no code blocks or monospace data displays appear in the UI.

### DevDependencies (pre-installed)

| Package | Purpose |
|---------|---------|
| `@types/node` / `@types/react` / `@types/react-dom` | Type definitions |
| `eslint` / `eslint-config-next` | Linting |

### Full Install Commands

```bash
# Initialize project (shadcn handles Next.js + Tailwind + TypeScript + core deps)
echo "my-app" | npx shadcn@latest init --yes --template next --base-color stone

# shadcn/ui components used in the app
npx shadcn add button card badge input avatar textarea skeleton switch dropdown-menu

# Animation library
npm install framer-motion

# State management
npm install zustand
```

---

## 3. Component Inventory

### 3.1 shadcn/ui Components

| Component | Source | Usage | Customization |
|-----------|--------|-------|---------------|
| `Button` | `shadcn add button` | All CTA buttons (primary, secondary, ghost, neon variants) | Add `neon` variant via CVA; custom border-radius (12px), glow animation |
| `Card` | `shadcn add card` | Feature cards, dashboard cards, medication cards | Add `glass` / `elevated` / `dark` variants; glassmorphism backdrop-blur |
| `Badge` | `shadcn add badge` | Status indicators, medication status, confidence labels | Add `outline` variant; pill border-radius (20px) |
| `Input` | `shadcn add input` | Chat text input | Custom border-radius (14px), focus ring with green glow |
| `Textarea` | `shadcn add textarea` | Chat multi-line input (auto-resize) | Same styling as Input; max 5 rows |
| `Avatar` | `shadcn add avatar` | User profile, AI avatar | Size variants (sm/md/lg); fallback initials |
| `Skeleton` | `shadcn add skeleton` | Loading states for chat, dashboard | Shimmer animation via CSS gradient + keyframes |
| `Switch` | `shadcn add switch` | Settings toggle | Custom track/thumb sizing; green active state |
| `DropdownMenu` | `shadcn add dropdown-menu` | Chat "More" actions (Clear, Export, Help) | Standard styling |

### 3.2 Custom Components

| Component | Props | Description |
|-----------|-------|-------------|
| `NeonButton` | `children`, `onClick`, `size?`, `disabled?` | Primary CTA with pulsing blue glow animation (`neonPulse` variant). Wraps shadcn Button with added animation layer. |
| `GlassCard` | `children`, `variant?`, `className?` | Card with `backdrop-filter: blur(12px)`, semi-transparent bg/border/shadow. Extends shadcn Card. |
| `IconButton` | `icon`, `onClick`, `variant?`, `badge?` | 40×40 circular/rounded button for icon-only actions. Tooltip support. |
| `ToggleSwitch` | `checked`, `onChange`, `label?` | Binary on/off switch. Wraps shadcn Switch with label. |
| `SkeletonLoader` | `count?`, `type?: 'text' \| 'card' \| 'avatar'` | Loading placeholder with shimmer keyframe animation. |
| `ToastNotification` | `message`, `type`, `onDismiss`, `action?` | Auto-dismissing toast (4s). Types: success/info/warning. Slide-in from right (left in RTL). |
| `HexagonGrid` | `className?` | Decorative SVG hexagon honeycomb pattern for hero background. |
| `FloatingParticles` | `count?`, `colors?` | Canvas-based floating particle system (upward drift + sway). |
| `GlowOrbs` | `count?`, `colors?` | Large radial gradient orbs with slow drift animation. |
| `TypingIndicator` | `visible` | Three bouncing dots with staggered animation. |
| `AnimatedMessage` | `content`, `sender: 'user' \| 'ai'`, `timestamp`, `type?` | Chat bubble with slide-in entrance (from right for user, left for AI). Supports embedded cards. |
| `QuickActionChip` | `label`, `onClick`, `icon?` | Clickable pill-shaped chip for welcome message quick actions. |
| `ScheduleItem` | `time`, `title`, `icon`, `status` | Single row in Today's Schedule card. Three visual states (completed/upcoming/current). |
| `MedicationItem` | `name`, `dosage`, `frequency`, `status` | Medication card with status badge. Highlight animation on new addition. |
| `InsightCard` | `title`, `description`, `confidence`, `type` | Health insight mini-card with colored left border. Slide-in animation on new. |
| `ConnectionStatus` | `connected` | Pulsing dot + "Live Updates" label at dashboard bottom. |
| `NavLink` | `href`, `label`, `icon` | Sidebar navigation item with hover/active states and left-border indicator. |
| `LanguageToggle` | `className?` | EN/AR toggle button with Globe icon. Updates global direction state. |
| `ScrollIndicator` | `visible` | Animated dot moving down a thin line. Fades out on scroll. |
| `TrustBadge` | `icon`, `label` | Icon + label row for CTA section trust indicators. |
| `FeatureCard` | `icon`, `title`, `description` | Elevated card with top green accent bar that expands on hover. |
| `AgentFlowCard` | `step`, `name`, `role`, `description`, `position: 'left' \| 'right'` | Agent card for How It Works section with connector to timeline. |

### 3.3 Section Components (per page)

**Landing Page (`/`)** — all in `app/sections/landing/`

| Component | Description |
|-----------|-------------|
| `NavigationBar` | Fixed nav with scroll-aware glass background. Logo + links + LanguageToggle + CTA button. |
| `HeroSection` | Full-viewport dark hero. Headline + subtext + NeonButton + ScrollIndicator + HexagonGrid + FloatingParticles + GlowOrbs. |
| `FeaturesSection` | 3-column feature card grid (Smart Chat, Care Dashboard, AI Personalization). |
| `HowItWorksSection` | Dark section with vertical timeline of 5 AI agents, alternating left/right cards. |
| `CTASection` | Warm CTA section with headline + button + 3 trust badges. |
| `FooterSection` | Dark footer with logo, links, copyright. |

**Main App (`/app`)** — all in `app/sections/app/`

| Component | Description |
|-----------|-------------|
| `Sidebar` | Collapsible left nav (260px/72px). Logo + 4 nav items + collapse toggle + user profile. |
| `TopBar` | Sticky chat header with title, LanguageToggle, notification + more menu buttons. |
| `ChatInterface` | Full-height chat column. Messages scroll area + sticky input bar (textarea + attach + send). |
| `CareDashboard` | Right panel (380px). Schedule + Medications + Insights cards + connection status. |

### 3.4 Custom Hooks

| Hook | Purpose |
|------|---------|
| `useDirection` | Subscribe to Zustand direction store. Returns `dir`, `isRTL`, `toggleDirection`. Applies `dir` to `<html>`. |
| `useSidebar` | Subscribe to sidebar collapse state. Returns `collapsed`, `toggleSidebar`. |
| `useWebSocket` | Simulated WebSocket connection. Returns `connected`, `lastEvent`, `send`. Fires random mock events every 5–15s. |
| `useAutoScroll` | Auto-scroll container to bottom on content change. Used in chat messages area. |
| `useTypingSimulator` | Simulates AI typing delay then reveals message. Returns `isTyping`, `displayedText`. |
| `useScrollTrigger` | Returns boolean when scroll position crosses threshold. Used for nav glass effect + scroll indicator. |
| `useLocalStorage` | Persist language preference and sidebar state across sessions. |

---

## 4. Animation Implementation Table

| Animation | Library | Implementation Approach | Complexity |
|-----------|---------|------------------------|------------|
| Page transitions (fade + slide) | Framer Motion | `AnimatePresence` wrapping page content. Exit: opacity→0 (0.2s). Enter: opacity 0→1, y:20→0 (0.4s). | Low |
| Hero entrance sequence | Framer Motion | `staggerChildren` container. Headline (0.8s, delay 0.3s) → Subtext (0.7s, delay 0.5s) → CTA (0.5s, delay 0.7s) → Scroll indicator (0.5s, delay 1.2s). | Medium |
| Nav scroll-aware glass background | CSS + Hook | `useScrollTrigger` at 50px threshold toggles class. CSS transition on background/border (0.3s). | Low |
| Nav link underline hover | CSS | `::after` pseudo-element, `width: 0→100%`, `transform-origin: left`, 0.25s ease. | Low |
| Nav entrance (fade from top) | Framer Motion | `initial={{ opacity: 0, y: -20 }}` → `animate={{ opacity: 1, y: 0 }}`, 0.5s, delay 0.2s. | Low |
| Fade in up (scroll-triggered) | Framer Motion | `whileInView` with `viewport={{ once: true, margin: "-100px" }}`. `hidden: { opacity: 0, y: 30 }` → `visible: { opacity: 1, y: 0 }`, 0.6s. | Low |
| Fade in scale | Framer Motion | `hidden: { opacity: 0, scale: 0.95 }` → `visible: { opacity: 1, scale: 1 }`, 0.4s. | Low |
| Stagger container | Framer Motion | Parent: `staggerChildren: 0.1, delayChildren: 0.1`. Children use `fadeInUp` or `fadeInScale`. | Low |
| Card hover lift | Framer Motion | `whileHover={{ y: -2, boxShadow: "..." }}`, 0.3s ease. | Low |
| Feature card top-border expand | CSS | `::before` pseudo-element, `width: 40px→100%`, 0.4s ease on hover. | Low |
| Hexagon grid slow rotation | CSS | `@keyframes rotate { to { transform: rotate(1deg) } }`, `animation: rotate 60s linear infinite`. SVG hexagon pattern. | Low |
| Floating particles | Canvas API | Custom `<canvas>` element. 30 particles with upward drift, horizontal sine sway, fade in/out. `requestAnimationFrame` loop. | **High** |
| Glow orbs slow drift | CSS | `@keyframes drift` translating `transform: translate()`, 20s infinite ease-in-out. Radial gradient divs. | Low |
| Neon button pulse glow | Framer Motion | `animate={{ boxShadow: ["0 0 10px ...", "0 0 25px ...", "0 0 10px ..."] }}`, 2s infinite. | Low |
| Scroll indicator dot bounce | CSS | `@keyframes bounce { 0%,100% { top: 0 } 50% { top: 100% } }`, 2s infinite ease-in-out. | Low |
| Scroll indicator fade-out | Framer Motion | `animate={{ opacity: scrollY > 100 ? 0 : 1 }}`. | Low |
| How It Works vertical line draw | Framer Motion | `initial={{ scaleY: 0 }}` → `whileInView={{ scaleY: 1 }}`, `transform-origin: top`, 1s. | Medium |
| Agent cards alternating slide-in | Framer Motion | Left cards: `x: -60→0`. Right cards: `x: 60→0`. Stagger 0.2s. `whileInView`. | Medium |
| Agent card glow pulse on appear | Framer Motion | One-time `boxShadow` pulse: `--glow-green` for 2s, then settle. Triggered `onViewportEnter`. | Low |
| Step number circle scale-in | Framer Motion | `fadeInScale` triggered when parent card enters viewport. | Low |
| CTA trust badges stagger | Framer Motion | `staggerContainer` with `fadeInScale`, delay 0.4s, stagger 0.1s. | Low |
| **Sidebar expand/collapse** | CSS + Framer Motion | Width transition 0.35s `cubic-bezier(0.4,0,0.2,1)`. Content fades via `AnimatePresence`. Nav labels fade in/out. | Medium |
| Sidebar slide-in on load | Framer Motion | `initial={{ x: -20, opacity: 0 }}` → `animate={{ x: 0, opacity: 1 }}`, 0.4s, delay 0.1s. | Low |
| Nav item hover/active | CSS | Background + color transition 0.2s. Active left border: `scaleY: 0→1`, `transform-origin: center`. | Low |
| Tooltip (collapsed sidebar) | Framer Motion | `AnimatePresence` + `fadeInScale` (0.15s). Positioned absolute to right of icon. | Low |
| **Chat message slide-in** | Framer Motion | User: `x: 30→0`. AI: `x: -30→0`. Both with `opacity: 0→1`. Spring: `{ stiffness: 400, damping: 35 }`. `AnimatePresence` for exit. | Medium |
| Typing indicator dots bounce | Framer Motion | `animate={{ y: [0, -6, 0] }}`, 0.6s infinite, `ease: "easeInOut"`. Staggered by 0.15s per dot. | Low |
| Typing indicator appear/disappear | Framer Motion | Appear: `fadeInScale`, 0.2s. Disappear: `opacity: 1→0`, 0.15s. | Low |
| **AI message character-by-character reveal** | Framer Motion + Hook | `useTypingSimulator` progressively reveals text over 1–3s based on length. Uses `setInterval` with 30ms per char. | **High** |
| Auto-scroll to bottom | JS | `useAutoScroll` hook. `scrollTo({ behavior: 'smooth', top: scrollHeight })`. | Low |
| Welcome message entrance | Framer Motion | `fadeInUp`, delay 0.3s. Quick action chips: `staggerContainer`, stagger 0.08s, delay 0.6s. | Low |
| Quick action chip hover | CSS | Background darkens, border turns `--accent-green`. 0.2s transition. | Low |
| **Dashboard slide-in** | Framer Motion | `slideInRight`: `x: 100→0`, `opacity: 0→1`. Spring: `{ stiffness: 300, damping: 30 }`. 0.4s, delay 0.2s. | Low |
| Dashboard cards stagger | Framer Motion | `staggerContainer`, stagger 0.12s. Each card: `fadeInUp` + scale. | Low |
| Schedule item flash on update | CSS | Brief `--warning` background at 20% opacity, fades over 1s via CSS transition. | Low |
| **Medication added animation** | Framer Motion | New item: `fadeInScale` + `y: -20→0`, 0.4s. Border glow pulse: `--glow-green` for 2s. | Medium |
| **New insight slide-in** | Framer Motion | `x: 50→0`, `opacity: 0→1`, 0.4s. Brief `--glow-blue` border glow for 2s. Existing items shift down via layout animation. | Medium |
| Connection status dot pulse | CSS | `@keyframes pulse { 0%,100% { scale:1; opacity:1 } 50% { scale:1.5; opacity:0.5 } }`, 2s infinite. | Low |
| **Toast enter/exit/stack** | Framer Motion | Enter: `x: 100→0`, `opacity: 0→1`, spring `{ stiffness: 300, damping: 25 }`, 0.35s. Exit: `x: 0→100`, `opacity: 1→0`, 0.25s. Stack: `AnimatePresence` with `layout` prop for smooth y-shift. | **High** |
| Toast auto-dismiss | JS | `setTimeout(4000)` triggers exit animation, then removes from store. | Low |
| Skeleton shimmer | CSS | `@keyframes shimmer { background-position: -200% → 200% }`, 1.5s infinite. Linear gradient background. | Low |
| RTL layout flip | CSS + Zustand | `dir` attribute on `<html>`. Tailwind `rtl:` variants. Logical properties (`ms-`, `me-`, `ps-`, `pe-`). Flex `row-reverse` in RTL. | Medium |
| Input focus glow | CSS | `focus:ring-[3px] focus:ring-[rgba(77,105,78,0.15)] focus:border-[--accent-green]`, 0.2s transition. | Low |
| Button hover effects | CSS | Background lightens, shadow deepens. 0.25s `cubic-bezier(0.4,0,0.2,1)`. | Low |
| Send button active state | Framer Motion | `whileTap={{ scale: 0.95 }}`. | Low |

---

## 5. State & Logic Plan

### 5.1 Global State (Zustand)

**`useAppStore`** — single store with slices:

| Slice | State | Actions |
|-------|-------|---------|
| `direction` | `dir: 'ltr' \| 'rtl'` | `toggleDirection()` |
| `sidebar` | `collapsed: boolean` | `toggleSidebar()` |
| `language` | `lang: 'en' \| 'ar'` | `setLanguage(lang)` |
| `chat` | `messages: Message[]`, `isTyping: boolean` | `addMessage(msg)`, `setTyping(bool)`, `clearChat()` |
| `dashboard` | `schedule: ScheduleItem[]`, `medications: Medication[]`, `insights: Insight[]`, `notifications: Toast[]` | `addMedication(med)`, `updateSchedule(item)`, `addInsight(insight)`, `addNotification(n)`, `dismissNotification(id)` |
| `websocket` | `connected: boolean`, `lastEvent: WebSocketEvent \| null` | `setConnected(bool)`, `receiveEvent(event)` |

### 5.2 WebSocket Mock Architecture

No external WebSocket library needed. A custom `useWebSocket` hook simulates the connection:

```
useWebSocket hook:
├── on mount: set connected=true, start interval
├── interval (5–15s random): pick random event type, generate payload, call receiveEvent()
├── event types: medication_added, schedule_updated, insight_generated, chat_typing_start, chat_message, notification
├── on unmount: clear interval, set connected=false
└── exposes: connected, lastEvent
```

Event flow:
1. Hook generates random event
2. Zustand `receiveEvent()` updates appropriate slice
3. React components subscribe to relevant slice, re-render with animation
4. Dashboard cards animate updates via Framer Motion `AnimatePresence` + `layout`

### 5.3 RTL Architecture

```
DirectionProvider (root layout):
├── reads `dir` from Zustand store
├── applies `<html dir={dir}>`
├── provides `isRTL` context to children
└── all horizontal transforms conditionally swap:
    - sidebar slides from right when RTL
    - chat messages: user-left, AI-right when RTL
    - toast enters from left when RTL
    - dashboard slides from left when RTL
```

Tailwind `rtl:` modifier handles most layout flipping automatically. Custom Framer Motion animations read `isRTL` to swap `x` directions.

### 5.4 Chat Message Flow

```
User types message → presses Enter:
1. addMessage({ sender: 'user', content, timestamp }) to store
2. Message appears with right-slide animation (left-slide in RTL)
3. Auto-scroll to bottom
4. After 0.5s delay: setTyping(true)
5. Typing indicator appears with bounce animation
6. After 1–3s: AI response generated (simulated)
7. setTyping(false), addMessage({ sender: 'ai', content, timestamp })
8. AI message appears with left-slide animation
9. WebSocket event may fire to update dashboard
10. Auto-scroll to bottom
```

### 5.5 Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| `≥1280px` (xl) | Full 3-column: sidebar (260px) + chat (flex) + dashboard (380px) |
| `768–1279px` (md–lg) | 2-column: sidebar (72px collapsed) + chat. Dashboard as toggleable right overlay (380px) with backdrop blur |
| `<768px` (sm) | Single column: chat full-width. Sidebar as left drawer. Dashboard as bottom sheet (70% height) |

Sidebar state is managed independently per breakpoint via `useEffect` + `window.matchMedia`.

### 5.6 Data Flow Summary

```
Landing Page:
  Static content, no global state
  Local state: none (links scroll or navigate)

Main App:
  Zustand Store (central)
    ├── Sidebar ←→ sidebar slice
    ├── Chat    ←→ chat slice (+ typing simulation)
    ├── Dashboard ←→ dashboard slice
    └── WebSocket ←→ websocket slice (mock events)
```

---

## 6. Project File Structure

```
my-app/
├── app/
│   ├── layout.tsx                 # Root layout: fonts, DirectionProvider, metadata
│   ├── page.tsx                   # Landing page (composes landing sections)
│   ├── globals.css                # Tailwind imports, custom CSS variables, keyframes
│   │
│   ├── app/                       # Main app route (/app)
│   │   ├── layout.tsx             # App layout: 3-column flex container
│   │   └── page.tsx               # Composes: Sidebar + ChatInterface + CareDashboard
│   │
│   ├── sections/
│   │   ├── landing/               # Landing page sections
│   │   │   ├── NavigationBar.tsx
│   │   │   ├── HeroSection.tsx
│   │   │   ├── FeaturesSection.tsx
│   │   │   ├── HowItWorksSection.tsx
│   │   │   ├── CTASection.tsx
│   │   │   └── FooterSection.tsx
│   │   │
│   │   └── app/                   # Main app sections
│   │       ├── Sidebar.tsx
│   │       ├── TopBar.tsx
│   │       ├── ChatInterface.tsx
│   │       └── CareDashboard.tsx
│   │
│   ├── components/                # Reusable custom components
│   │   ├── ui/                    # shadcn components (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── input.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── switch.tsx
│   │   │   └── dropdown-menu.tsx
│   │   │
│   │   ├── NeonButton.tsx
│   │   ├── GlassCard.tsx
│   │   ├── IconButton.tsx
│   │   ├── ToastNotification.tsx
│   │   ├── HexagonGrid.tsx
│   │   ├── FloatingParticles.tsx
│   │   ├── GlowOrbs.tsx
│   │   ├── TypingIndicator.tsx
│   │   ├── AnimatedMessage.tsx
│   │   ├── QuickActionChip.tsx
│   │   ├── ScheduleItem.tsx
│   │   ├── MedicationItem.tsx
│   │   ├── InsightCard.tsx
│   │   ├── ConnectionStatus.tsx
│   │   ├── NavLink.tsx
│   │   ├── LanguageToggle.tsx
│   │   ├── ScrollIndicator.tsx
│   │   ├── TrustBadge.tsx
│   │   ├── FeatureCard.tsx
│   │   ├── AgentFlowCard.tsx
│   │   └── SkeletonLoader.tsx
│   │
│   ├── hooks/
│   │   ├── useDirection.ts
│   │   ├── useSidebar.ts
│   │   ├── useWebSocket.ts
│   │   ├── useAutoScroll.ts
│   │   ├── useTypingSimulator.ts
│   │   ├── useScrollTrigger.ts
│   │   └── useLocalStorage.ts
│   │
│   ├── store/
│   │   └── useAppStore.ts         # Zustand store with all slices
│   │
│   ├── types/
│   │   └── index.ts               # TypeScript types (Message, ScheduleItem, Medication, Insight, Toast, WebSocketEvent)
│   │
│   ├── lib/
│   │   ├── utils.ts               # cn() utility (shadcn default)
│   │   └── animations.ts          # Shared Framer Motion variants (fadeInUp, fadeInScale, staggerContainer, slideInLeft, slideInRight, messageAppear, typingDot, neonPulse, cardHover)
│   │
│   └── data/
│       └── mockData.ts            # Initial mock data (schedule items, medications, insights, sample chat messages)
│
├── components/ui/                 # shadcn components (alternative location — keep consistent)
├── public/
│   ├── images/                    # Generated/downloaded assets
│   │   ├── ai-avatar.png
│   │   ├── user-avatar.png
│   │   ├── hero-bg-gradient.jpg
│   │   ├── feature-chat.png
│   │   ├── feature-dashboard.png
│   │   └── feature-ai.png
│   └── fonts/                     # (if not using next/font)
│
├── tailwind.config.ts             # Custom colors, fonts, breakpoints, animations
├── next.config.js                 # Output: export, images: unoptimized
├── tsconfig.json
└── package.json
```

---

## 7. Tailwind Configuration Plan

### Custom Theme Extensions

```typescript
// tailwind.config.ts
{
  theme: {
    extend: {
      colors: {
        'nerve-bg': '#FFF7E6',
        'nerve-bg-secondary': '#FFF3D5',
        'nerve-dark': '#00311F',
        'nerve-green': '#4D694E',
        'nerve-green-light': '#6B8F6C',
        'nerve-blue': '#2563EB',
        'nerve-cyan': '#06B6D4',
        'nerve-muted': '#6B7B6C',
      },
      fontFamily: {
        inter: ['var(--font-inter)', 'sans-serif'],
        arabic: ['var(--font-noto-sans-arabic)', 'sans-serif'],
      },
      animation: {
        'shimmer': 'shimmer 1.5s infinite',
        'neon-pulse': 'neonPulse 2s ease-in-out infinite',
        'float': 'float 20s ease-in-out infinite',
        'bounce-dot': 'bounceDot 0.6s ease-in-out infinite',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        neonPulse: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(37,99,235,0.3)' },
          '50%': { boxShadow: '0 0 25px rgba(37,99,235,0.5)' },
        },
        float: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(20px, -20px)' },
        },
        bounceDot: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        pulseDot: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.5)', opacity: '0.5' },
        },
      },
    },
  },
}
```

---

## 8. Key Implementation Notes

### 8.1 No Third-Party Animation Libraries
All animations use Framer Motion (declarative React animations) or pure CSS keyframes. No GSAP, Lottie, or other animation libraries needed.

### 8.2 Floating Particles Implementation
The FloatingParticles component uses raw Canvas API (not a library):
- `<canvas>` element positioned absolute, full-size of parent
- `useEffect` initializes particle array (30 particles with random position, velocity, size, opacity)
- `requestAnimationFrame` loop updates positions and redraws
- Particles drift upward with `Math.sin()` horizontal sway
- Opacity fades near top/bottom edges
- Cleanup on unmount stops animation frame

### 8.3 WebSocket Mock
The `useWebSocket` hook does NOT use Socket.io or native WebSocket:
- Pure `setInterval` with random delay (5–15s)
- Randomly selects event type from predefined list
- Generates realistic mock payload
- Dispatches to Zustand store
- This satisfies the requirement for "real-time updates" without backend dependency

### 8.4 AI Typing Simulation
The `useTypingSimulator` hook:
- Accepts `fullText` and `speedMs` (default 30ms per char)
- Uses `setInterval` to progressively reveal characters
- Calculates duration: `fullText.length * speedMs`
- Returns `{ displayedText, isComplete }`
- Triggered when `isTyping` goes true in the store

### 8.5 RTL Layout Strategy
- Zustand `direction` slice holds `'ltr'` or `'rtl'`
- Root `layout.tsx` reads direction and applies `<html dir={dir} lang={lang}>`
- Tailwind's built-in `rtl:` prefix handles most layout flipping (e.g., `rtl:mr-4 rtl:ml-0`)
- Framer Motion animations read `isRTL` from `useDirection` and swap `x` values (e.g., user message enters from `-30` in RTL instead of `30`)
- Sidebar and dashboard panel swap sides in RTL mode

### 8.6 Image Assets
All images listed in design.md `[ASSET: ...]` tags will be generated or sourced during development. Hero background and feature illustrations use AI image generation. Avatars use generated profile images. No external image dependencies at build time.

### 8.7 Performance Considerations
- `viewport={{ once: true }}` on all scroll-triggered animations to prevent re-animation
- Canvas particles use `will-change: transform` for GPU acceleration
- Zustand selectors prevent unnecessary re-renders (subscribe to specific slices)
- Dashboard card `layout` prop in Framer Motion enables smooth repositioning without full re-render
- `React.memo` on message bubbles and dashboard cards to prevent re-render on unrelated state changes
