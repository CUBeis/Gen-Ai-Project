import { motion } from 'framer-motion';
import { fadeInUp, staggerContainer } from '@/lib/animations';

const languages = [
  { name: 'English', flag: '🇺🇸', desc: 'Internal reasoning & medical terminology' },
  { name: 'العربية', flag: '🇸🇦', desc: 'RTL supported for Arabic' },
];

export function MultilingualSection() {
  return (
    <section className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(107, 143, 108,0.2)] to-transparent" />

      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left - Content */}
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4D694E]" />
              <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#4D694E]">
                Multilingual
              </span>
            </div>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
              Speak Every
              <br />
              <span className="text-gradient-purple">Patient's Language</span>
            </h2>
            <p className="mt-6 text-[rgba(0,0,0,0.5)] leading-relaxed max-w-md">
              Internal reasoning in English, external communication in the patient's language.
              Full support for Arabic, with multilingual embedding models that understand
              medical terminology across languages.
            </p>
          </motion.div>

          {/* Right - Language Cards */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="flex flex-col gap-4"
          >
            {languages.map((lang) => (
              <motion.div
                key={lang.name}
                variants={fadeInUp}
                whileHover={{ x: 4 }}
                className="p-6 rounded-xl bg-[rgba(0,0,0,0.02)] border border-[rgba(0,0,0,0.06)] hover:border-[#6B8F6C] hover:shadow-[0_0_16px_rgba(107,143,108,0.2)] transition-all cursor-default"
              >
                <div className="flex items-center gap-4">
                  <span className="text-3xl">{lang.flag}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{lang.name}</h3>
                    <p className="text-sm text-[rgba(0,0,0,0.5)]">{lang.desc}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
