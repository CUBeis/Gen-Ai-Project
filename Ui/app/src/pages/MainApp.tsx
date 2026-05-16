import { useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Sidebar } from '@/sections/app/Sidebar';
import { ChatInterface } from '@/sections/app/ChatInterface';
import { CareDashboard } from '@/sections/app/CareDashboard';
import { ToastContainer } from '@/components/ToastNotification';

export default function MainApp() {
  useWebSocket(true);

  useEffect(() => {
    // Ensure scroll is at top
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-nerve-bg">
      <ToastContainer />
      <Sidebar />
      <ChatInterface />
      <CareDashboard />
    </div>
  );
}
