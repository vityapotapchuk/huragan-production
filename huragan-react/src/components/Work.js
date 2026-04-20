import React, { useState, useRef, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';

const projects = [
  { cat: 'commercial', title: 'Brand X — Ad Campaign', bg: 'linear-gradient(135deg,#6C5CE7,#a29bfe)', label: 'Commercial', wide: false },
  { cat: 'music', title: 'Ocean — Cinematic Visual', bg: 'linear-gradient(135deg,#00CEC9,#55efc4)', label: 'Music Video', wide: true },
  { cat: 'corporate', title: 'TechCorp — Brand Film', bg: 'linear-gradient(135deg,#FD79A8,#e84393)', label: 'Corporate', wide: false },
  { cat: 'documentary', title: 'The Way Home', bg: 'linear-gradient(135deg,#FDCB6E,#f39c12)', label: 'Documentary', wide: false },
  { cat: 'commercial', title: 'Fashion Week — Promo', bg: 'linear-gradient(135deg,#E17055,#d63031)', label: 'Commercial', wide: true },
  { cat: 'music', title: 'Night City — Lyric Video', bg: 'linear-gradient(135deg,#74b9ff,#0984e3)', label: 'Music Video', wide: false },
];

const Work = () => {
  const [filter, setFilter] = useState('all');
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  const filters = ['all', 'commercial', 'music', 'corporate', 'documentary'];

  return (
    <section className="section work" id="work" ref={ref}>
      <div className="container">
        <motion.div className="section-header" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6 }}>
          <div className="section-tag">Selected Work</div>
          <h2 className="section-title">Projects that <span className="accent">speak volumes</span></h2>
        </motion.div>
        <motion.div className="work-filters" initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ delay: 0.2, duration: 0.5 }}>
          {filters.map(f => (
            <button key={f} className={`filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </motion.div>
        <div className="work-grid">
          {projects.filter(p => filter === 'all' || p.cat === filter).map((p, i) => (
            <motion.div
              key={p.title}
              className={`work-item ${p.wide ? 'wide' : ''}`}
              layout
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <div className="work-thumb" style={{ background: p.bg }}>
                <div className="work-play">▶</div>
                <div className="work-info">
                  <span className="work-cat">{p.label}</span>
                  <h3>{p.title}</h3>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Work;