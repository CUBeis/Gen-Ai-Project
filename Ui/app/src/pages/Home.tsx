import { NavigationBar } from '@/sections/landing/NavigationBar';
import { HeroSection } from '@/sections/landing/HeroSection';
import { ArchitectureSection } from '@/sections/landing/ArchitectureSection';
import { IntelligenceSection } from '@/sections/landing/IntelligenceSection';
import { VisionAgentSection } from '@/sections/landing/VisionAgentSection';
import { MultilingualSection } from '@/sections/landing/MultilingualSection';
import { MemorySection } from '@/sections/landing/MemorySection';
import { InterfaceSection } from '@/sections/landing/InterfaceSection';
import { SafetySection } from '@/sections/landing/SafetySection';
import { CTASection } from '@/sections/landing/CTASection';
import { FooterSection } from '@/sections/landing/FooterSection';

export default function Home() {
  return (
    <div className="min-h-screen bg-[#FFF7E6]">
      <NavigationBar />
      <main>
        <HeroSection />
        <ArchitectureSection />
        <IntelligenceSection />
        <VisionAgentSection />
        <MultilingualSection />
        <MemorySection />
        <InterfaceSection />
        <SafetySection />
        <CTASection />
      </main>
      <FooterSection />
    </div>
  );
}
