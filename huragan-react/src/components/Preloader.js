import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const Preloader = () => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) { clearInterval(interval); return 100; }
        return prev + Math.random() * 15 + 5;
      });
    }, 150);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      className="preloader"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.6 }}
    >
      <div className="preloader-inner">
        <div className="preloader-logo">HURAGAN</div>
        <div className="preloader-bar">
          <motion.div
            className="preloader-progress"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(progress, 100)}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <div className="preloader-percent">{Math.round(Math.min(progress, 100))}%</div>
      </div>
    </motion.div>
  );
};

export default Preloader;