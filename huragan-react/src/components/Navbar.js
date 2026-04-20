import React, { useState, useEffect } from 'react';

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleLink = () => setMenuOpen(false);

  return (
    <>
      <nav className={`nav ${scrolled ? 'scrolled' : ''}`}>
        <div className="nav-inner container">
          <a href="#" className="nav-logo">
            <span className="nav-logo-mark">H</span>
            <span className="nav-logo-text">HURAGAN</span>
          </a>
          <div className="nav-links">
            <a href="#work" className="nav-link">Work</a>
            <a href="#services" className="nav-link">Services</a>
            <a href="#about" className="nav-link">About</a>
            <a href="#contact" className="nav-link">Contact</a>
          </div>
          <a href="#contact" className="nav-cta">Start a Project</a>
          <button className={`nav-burger ${menuOpen ? 'active' : ''}`} onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu">
            <span></span><span></span>
          </button>
        </div>
      </nav>
      <div className={`mobile-menu ${menuOpen ? 'active' : ''}`}>
        <div className="mobile-menu-inner">
          <a href="#work" className="mobile-link" onClick={handleLink}>Work</a>
          <a href="#services" className="mobile-link" onClick={handleLink}>Services</a>
          <a href="#about" className="mobile-link" onClick={handleLink}>About</a>
          <a href="#contact" className="mobile-link" onClick={handleLink}>Contact</a>
          <a href="#contact" className="btn btn-primary mobile-cta" onClick={handleLink}>Start a Project</a>
        </div>
      </div>
    </>
  );
};

export default Navbar;