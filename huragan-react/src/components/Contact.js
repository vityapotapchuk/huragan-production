import React, { useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const Contact = () => {
  const [sent, setSent] = useState(false);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  const handleSubmit = (e) => {
    e.preventDefault();
    setSent(true);
    setTimeout(() => { setSent(false); e.target.reset(); }, 3000);
  };

  return (
    <section className="section contact" id="contact" ref={ref}>
      <div className="container">
        <motion.div className="section-header" initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6 }}>
          <div className="section-tag">Get in Touch</div>
          <h2 className="section-title">Let's make something <span className="accent">epic</span></h2>
        </motion.div>
        <div className="contact-grid">
          <motion.form className="contact-form" onSubmit={handleSubmit} initial={{ opacity: 0, x: -30 }} animate={inView ? { opacity: 1, x: 0 } : {}} transition={{ delay: 0.2, duration: 0.6 }}>
            <div className="form-group">
              <label>Your Name</label>
              <input type="text" placeholder="John Doe" required />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" placeholder="john@example.com" required />
            </div>
            <div className="form-group">
              <label>Project Type</label>
              <select required>
                <option value="" disabled selected>Select a type</option>
                <option>Commercial</option>
                <option>Music Video</option>
                <option>Corporate Video</option>
                <option>Documentary</option>
                <option>Motion Design</option>
                <option>Live Streaming</option>
                <option>Other</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tell Us About Your Project</label>
              <textarea placeholder="Share your vision..." rows="5" required></textarea>
            </div>
            <button type="submit" className="btn btn-primary btn-full" style={sent ? { background: 'var(--accent-2)', color: 'var(--text)' } : {}}>
              {sent ? '✓ Sent!' : 'Send Message'}
            </button>
          </motion.form>
          <motion.div className="contact-details" initial={{ opacity: 0, x: 30 }} animate={inView ? { opacity: 1, x: 0 } : {}} transition={{ delay: 0.3, duration: 0.6 }}>
            <div className="contact-card"><span className="contact-card-icon">📍</span><div><h4>Location</h4><p>Kyiv, Ukraine</p></div></div>
            <div className="contact-card"><span className="contact-card-icon">📧</span><div><h4>Email</h4><p>huragan.production@gmail.com</p></div></div>
            <div className="contact-card"><span className="contact-card-icon">📱</span><div><h4>Instagram</h4><p>@huragan.production</p></div></div>
            <div className="contact-card"><span className="contact-card-icon">🕐</span><div><h4>Working Hours</h4><p>Mon–Fri: 9:00 AM — 6:00 PM</p></div></div>
            <div className="contact-socials">
              <a href="https://www.instagram.com/huragan.production/" target="_blank" rel="noreferrer" className="social-btn">Instagram</a>
              <a href="#" className="social-btn">YouTube</a>
              <a href="#" className="social-btn">TikTok</a>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default Contact;