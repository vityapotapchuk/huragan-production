import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const services = [
  { icon: '🎬', name: 'Video Production', desc: 'Full-scale production with cinema cameras, drones, and professional lighting', color: '#6C5CE7' },
  { icon: '✂️', name: 'Editing & Post', desc: 'Precision cuts, color grading, and VFX that make every frame count', color: '#00CEC9' },
  { icon: '🎨', name: 'Motion Design', desc: 'Killer animations, graphics, and titles that elevate your story', color: '#FD79A8' },
  { icon: '📝', name: 'Scriptwriting', desc: 'From concept to script — we craft narratives that hit hard', color: '#FDCB6E' },
  { icon: '🔊', name: 'Sound Design', desc: 'Crystal-clear audio, immersive soundscapes, and pro voiceover', color: '#E17055' },
  { icon: '📡', name: 'Live Streaming', desc: 'Multi-cam live broadcasts that keep audiences locked in', color: '#74b9ff' },
];

const Services = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <section className="section services" id="services" ref={ref}>
      <div className="container">
        <motion.div className="section-header" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6 }}>
          <div className="section-tag">What We Do</div>
          <h2 className="section-title">Huragan Production <span className="accent">services</span></h2>
          <p className="section-subtitle">Everything you need to bring your vision to life — from first idea to final cut.</p>
        </motion.div>
        <div className="services-grid">
          {services.map((s, i) => (
            <motion.div
              key={s.name}
              className="service-card"
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              whileHover={{ y: -8, transition: { duration: 0.3 } }}
            >
              <div className="service-card-icon" style={{ background: s.color + '18', color: s.color }}>
                {s.icon}
              </div>
              <h3 className="service-card-title">{s.name}</h3>
              <p className="service-card-desc">{s.desc}</p>
              <div className="service-card-bar" style={{ background: s.color }}></div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Services;