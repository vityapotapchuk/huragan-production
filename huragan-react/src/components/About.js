import React, { useRef, useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';

const stats = [
  { target: 150, plus: true, label: 'Projects Delivered' },
  { target: 7, plus: false, label: 'Years in the Game' },
  { target: 40, plus: true, label: 'Happy Clients' },
  { target: 12, plus: false, label: 'Awards Won' },
];

const Counter = ({ target }) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    const duration = 2000;
    const start = performance.now();
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [inView, target]);

  return <span ref={ref}>{count}</span>;
};

const About = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <section className="section about" id="about" ref={ref}>
      <div className="container">
        <div className="about-grid">
          <motion.div className="about-left" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6 }}>
            <div className="section-tag">About Us</div>
            <h2 className="section-title">We don't just shoot video.<br /><span className="accent">We create impact.</span></h2>
            <p className="about-text">Huragan Production is a team of creators, dreamers, and storytellers. We live for the shot that gives you chills. The edit that makes you rewind. The story that stays with you.</p>
            <p className="about-text">From high-energy commercials to cinematic music videos — we bring the fire.</p>
          </motion.div>
          <motion.div className="about-right" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ delay: 0.2, duration: 0.6 }}>
            <div className="stats-grid">
              {stats.map((s, i) => (
                <motion.div key={i} className="stat-card" initial={{ opacity: 0, scale: 0.9 }} animate={inView ? { opacity: 1, scale: 1 } : {}} transition={{ delay: 0.3 + i * 0.1 }}>
                  <span className="stat-number"><Counter target={s.target} /></span>
                  {s.plus && <span className="stat-plus">+</span>}
                  <span className="stat-label">{s.label}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default About;