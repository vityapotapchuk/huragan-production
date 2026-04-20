import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const CTA = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <section className="cta" ref={ref}>
      <div className="container cta-inner">
        <motion.h2 className="cta-title" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6 }}>
          Got a project that<br />needs <span className="accent">fire</span>?
        </motion.h2>
        <motion.p className="cta-desc" initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ delay: 0.2, duration: 0.5 }}>
          Let's create something that people can't stop watching.
        </motion.p>
        <motion.a href="#contact" className="btn btn-primary btn-lg" initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ delay: 0.4, duration: 0.5 }}>
          Start a Project
        </motion.a>
      </div>
    </section>
  );
};

export default CTA;