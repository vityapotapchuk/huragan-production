import React from 'react';
import { motion } from 'framer-motion';

const Hero = () => {
  const lineVariants = {
    hidden: { y: 80, opacity: 0 },
    visible: (i) => ({
      y: 0,
      opacity: 1,
      transition: { delay: 0.3 + i * 0.15, duration: 0.8, ease: [0.16, 1, 0.3, 1] }
    })
  };

  return (
    <section className="hero" id="hero">
      <div className="hero-video-wrap">
        <div className="hero-video-overlay"></div>
        <div className="hero-video-placeholder"></div>
      </div>
      <div className="container hero-content">
        <motion.div
          className="hero-tag"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          CREATIVE VIDEO STUDIO
        </motion.div>
        <h1 className="hero-title">
          {['Let your', 'story be', 'really seen'].map((line, i) => (
            <motion.span
              key={i}
              className="hero-line"
              custom={i}
              variants={lineVariants}
              initial="hidden"
              animate="visible"
            >
              <span className={`hero-word ${i === 2 ? 'accent' : ''}`}>{line}</span>
            </motion.span>
          ))}
        </h1>
        <motion.p
          className="hero-desc"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.6 }}
        >
          Your story deserves more than just telling — it deserves to be truly seen, felt, and remembered.
        </motion.p>
        <motion.div
          className="hero-actions"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1, duration: 0.6 }}
        >
          <a href="#work" className="btn btn-primary">Explore Our Work</a>
          <a href="#contact" className="btn btn-ghost">Let's Talk</a>
        </motion.div>
      </div>
      <motion.div
        className="hero-scroll-indicator"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
      >
        <div className="scroll-line"></div>
        <span>Scroll to discover</span>
      </motion.div>
    </section>
  );
};

export default Hero;