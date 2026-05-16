import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { fadeInUp, staggerContainer } from '@/lib/animations';

const features = [
  'Semantic chunking with words context windows',
  'all-MiniLM-L6-v2 for medical embeddings',
  'Query reformulation with session context',
];

const steps = [
  { num: '01', title: 'Data Ingestion', desc: 'PDFs, CSVs, and clinical documents are parsed and chunked semantically using LangChain.' },
  { num: '02', title: 'Embedding', desc: 'Medical-grade embedding models create dense vector representations of each chunk.' },
  { num: '03', title: 'Vector Storage', desc: 'ChromaDB store vectors for fast similarity search across clinical knowledge.' },
  { num: '04', title: 'Augmented Response', desc: 'Retrieved context enriches the LLM prompt for precise, evidence-based answers.' },
];

export function IntelligenceSection() {
  return (
    <section id="intelligence" className="bg-[#FFF7E6] py-24 md:py-32 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[rgba(77, 105, 78,0.2)] to-transparent" />

      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
          {/* Left content */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            <motion.div variants={fadeInUp}>
              <div className="flex items-center gap-2 mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-[#6B8F6C]" />
                <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[#6B8F6C]">
                  Clinical Intelligence
                </span>
              </div>
              <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
                Medical-Grade
                <br />
                <span className="text-gradient-cyan">Retrieval</span>
              </h2>
            </motion.div>

            <motion.p
              variants={fadeInUp}
              className="mt-6 text-[rgba(0,0,0,0.5)] leading-relaxed max-w-md"
            >
              The Clinical RAG pipeline ingests medical documents, generates semantic
              embeddings, and retrieves relevant knowledge to augment every patient
              interaction with evidence-based context.
            </motion.p>

            <motion.ul variants={staggerContainer} className="mt-8 space-y-3">
              {features.map((f) => (
                <motion.li key={f} variants={fadeInUp} className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-[rgba(6,182,212,0.15)] flex items-center justify-center shrink-0 mt-0.5">
                    <Check className="w-3 h-3 text-[#6B8F6C]" />
                  </span>
                  <span className="text-sm text-[rgba(0,0,0,0.6)]">{f}</span>
                </motion.li>
              ))}
            </motion.ul>
          </motion.div>

          {/* Right - Pipeline image */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="rounded-2xl overflow-hidden border border-[rgba(0,0,0,0.05)]"
          >
            <img
              src="./images/rag-pipeline.png"
              alt="Clinical RAG Pipeline"
              className="w-full h-auto"
            />
          </motion.div>
        </div>

        {/* Steps */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {steps.map((step) => (
            <motion.div
              key={step.num}
              variants={fadeInUp}
              className="p-5 rounded-xl bg-[rgba(0,0,0,0.02)] border border-[rgba(0,0,0,0.05)] hover:border-[#9fc5e8] hover:shadow-[0_0_16px_rgba(159,197,232,0.3)] transition-all"
            >
              <span className="text-xs font-mono text-[rgba(0,0,0,0.3)]">{step.num}</span>
              <h4 className="mt-3 text-sm font-semibold text-gray-900">{step.title}</h4>
              <p className="mt-1.5 text-xs text-[rgba(0,0,0,0.4)] leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
