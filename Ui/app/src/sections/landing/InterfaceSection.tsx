import { motion } from 'framer-motion';
import { fadeInUp, fadeInScale } from '@/lib/animations';
import { useNavigate } from 'react-router';

export function InterfaceSection() {
  const navigate = useNavigate();

  return (
    <section className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(77, 105, 78,0.2)] to-transparent" />

      <div className="max-w-6xl mx-auto px-6 text-center">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mb-4"
        >
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#6B8F6C]" />
            <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#6B8F6C]">Interface</span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900">
            Where Agents Meet
            <br />
            <span className="text-gradient-cyan">Patients</span>
          </h2>
          <p className="mt-4 text-[rgba(0,0,0,0.5)] max-w-lg mx-auto">
            The patient web app splits into two connected spaces — an intelligent chat on
            the left, a dynamic care dashboard on the right. Both update in real-time via WebSocket.
          </p>
        </motion.div>

        <motion.div
          variants={fadeInScale}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="mt-12 relative"
        >
          <div
            className="rounded-2xl overflow-hidden border border-[rgba(0,0,0,0.08)] cursor-pointer group"
            onClick={() => navigate('/app')}
          >
            <img
              src="./images/patient web app.png"
              alt="Patient Dashboard Interface"
              className="w-full h-auto group-hover:scale-[1.02] transition-transform duration-500"
            />
          </div>

          {/* Click hint */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="mt-4 text-center"
          >
            <button
              onClick={() => navigate('/app')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-[rgba(77, 105, 78,0.15)] border border-[rgba(77, 105, 78,0.3)] text-[#4D694E] hover:bg-[rgba(77, 105, 78,0.25)] transition-colors"
            >
              Patient Dashboard
              <span className="text-lg">&#8594;</span>
            </button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
