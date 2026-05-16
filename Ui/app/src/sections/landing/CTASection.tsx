import { useNavigate } from 'react-router';
import { motion } from 'framer-motion';
import { fadeInUp, fadeInScale } from '@/lib/animations';

export function CTASection() {
  const navigate = useNavigate();

  return (
    <section className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(77, 105, 78,0.3)] to-transparent" />
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(77, 105, 78,0.08) 0%, transparent 60%)' }}
      />

      <div className="max-w-2xl mx-auto px-6 text-center relative z-10">
        <motion.h2
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight"
        >
          Ready to Transform your
          <br />
          <span className="text-gradient-purple">HealthCare experience ?</span>
        </motion.h2>

        <motion.p
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          transition={{ delay: 0.15 }}
          className="mt-5 text-[rgba(0,0,0,0.5)] max-w-md mx-auto"
        >
          Try our intelligent healthcare orchestration system that remembers,
          retrieves, and protects — in any language.
        </motion.p>

        <motion.div
          variants={fadeInScale}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-10"
        >
          <button
            onClick={() => navigate('/app')}
            className="px-8 py-3.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-[#6B8F6C] to-[#4D694E] text-gray-900 hover:opacity-90 transition-opacity shadow-glow"
          >
            TRY IT NOW
          </button>
        </motion.div>
      </div>
    </section>
  );
}
