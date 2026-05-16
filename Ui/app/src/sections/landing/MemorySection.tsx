import { motion } from 'framer-motion';
import { fadeInUp, fadeInScale } from '@/lib/animations';

export function MemorySection() {
  return (
    <section className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(6,182,212,0.2)] to-transparent" />

      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4D694E]" />
              <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#4D694E]">Memory</span>
            </div>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
              Two-Tier Memory
              <br />
              <span className="text-gradient-purple">Architecture</span>
            </h2>
            <p className="mt-6 text-[rgba(0,0,0,0.5)] leading-relaxed max-w-md">
              Short-term session memory maintains the immediate conversation context.
              Long-term episodic memory stores clinical insights in a vector database,
              enabling retrieval across patient sessions.
            </p>

            <div className="mt-10 flex gap-8">
              <div>
                <span className="text-4xl font-bold text-gray-900">20</span>
                <p className="mt-1 text-xs text-[rgba(0,0,0,0.4)]">Turns Sliding Window</p>
                <p className="text-[10px] text-[rgba(0,0,0,0.3)]">Short-Term Session</p>
              </div>
              <div>
                <span className="text-2xl font-bold text-gradient-cyan font-mono">Vector DB</span>
                <p className="mt-1 text-xs text-[rgba(0,0,0,0.4)]"></p>
                <p className="text-[10px] text-[rgba(0,0,0,0.3)]">Long-Term Episodic</p>
              </div>
            </div>
          </motion.div>

          {/* Right - Memory visualization */}
          <motion.div
            variants={fadeInScale}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="relative"
          >
            <div className="rounded-2xl border border-[rgba(0,0,0,0.06)] bg-[rgba(0,0,0,0.02)] p-8">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[rgba(77, 105, 78,0.15)] border border-[rgba(77, 105, 78,0.3)] flex items-center justify-center">
                    <div className="w-3 h-3 rounded-full bg-[#4D694E]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">SESSION</p>
                    <p className="text-[10px] text-[rgba(0,0,0,0.4)]">Active Context</p>
                  </div>
                </div>
                <div className="h-px flex-1 mx-6 border-t border-dashed border-[rgba(77, 105, 78,0.2)]" />
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[rgba(6,182,212,0.15)] border border-[rgba(6,182,212,0.3)] flex items-center justify-center">
                    <div className="w-3 h-3 rounded-full bg-[#6B8F6C]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">EPISODIC</p>
                    <p className="text-[10px] text-[rgba(0,0,0,0.4)]">Vector Storage</p>
                  </div>
                </div>
              </div>

              {/* Session memory visualization */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#4D694E]" />
                  <div className="h-8 flex-1 rounded-lg bg-[rgba(77, 105, 78,0.08)] border border-[rgba(77, 105, 78,0.15)]" />
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#4D694E]/70" />
                  <div className="h-8 flex-1 rounded-lg bg-[rgba(77, 105, 78,0.06)] border border-[rgba(77, 105, 78,0.1)]" />
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#4D694E]/50" />
                  <div className="h-8 flex-1 rounded-lg bg-[rgba(77, 105, 78,0.04)] border border-[rgba(77, 105, 78,0.08)]" />
                </div>
              </div>

              <div className="mt-4 flex items-center justify-center">
                <div className="flex items-center gap-2 text-[10px] text-[rgba(0,0,0,0.3)]">
                  <span>Patient Query</span>
                  <span className="text-[#4D694E]">&#8594;</span>
                  <span>Embedding</span>
                  <span className="text-[#6B8F6C]">&#8594;</span>
                  <span>Vector Search</span>
                  <span className="text-[#4D694E]">&#8594;</span>
                  <span>Retrieve</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
