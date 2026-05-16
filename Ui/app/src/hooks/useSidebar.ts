import { useAppStore } from '@/store/useAppStore';

export function useSidebar() {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  return { collapsed, toggleSidebar };
}
