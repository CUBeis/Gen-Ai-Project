import { motion } from 'framer-motion';
import { fadeInUp } from '@/lib/animations';

const capabilities = [
  'Medical image analysis and interpretation',
  'Multimodal understanding for holistic patient assessment',
  'Real-time image processing',
];

export function VisionAgentSection() {
  return (
    <section className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(251, 146, 60,0.2)] to-transparent" />

      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
          {/* Left - Image placeholder */}
          <motion.div
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="rounded-2xl overflow-hidden border border-[rgba(0,0,0,0.05)] bg-[rgba(251, 146, 60,0.05)] min-h-[400px] flex items-center justify-center order-2 lg:order-1"
          >
                        <img
              src="./images/Vision Agent.2.png"
              alt="Clinical RAG Pipeline"
              className="w-full h-auto"
            />
          </motion.div>

          {/* Right content */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="space-y-6 order-1 lg:order-2"
          >
            <motion.div variants={fadeInUp}>
              <div className="flex items-center gap-2 mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-[#fb923c]" />
                <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#fb923c]">
                  Vision Agent
                </span>
              </div>
              <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
              multiple inputs
                <br />
                <span className="text-gradient-orange">Supported</span>
              </h2>
            </motion.div>

            <motion.p
              variants={fadeInUp}
              className="leading-relaxed max-w-md text-[rgba(0,0,0,0.5)]"
            >
              The <span className="text-[#fb923c] font-medium">Vision Agent</span> processes medical images alongside clinical text,
              enabling comprehensive patient assessment. It understands medical imagery and integrates all inputs for more accurate clinical insights.
            </motion.p>

            <motion.ul
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              className="space-y-3 pt-4"
            >
              {capabilities.map((cap) => (
                <motion.li
                  key={cap}
                  variants={fadeInUp}
                  className="flex items-start gap-3"
                >
                  <span className="w-5 h-5 rounded-full bg-[rgba(251, 146, 60,0.15)] flex items-center justify-center shrink-0 mt-0.5">
                    <span className="w-2 h-2 rounded-full bg-[#fb923c]" />
                  </span>
                  <span className="text-sm text-[rgba(0,0,0,0.6)]">{cap}</span>
                </motion.li>
              ))}
            </motion.ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
