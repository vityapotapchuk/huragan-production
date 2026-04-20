import React from 'react';

const Marquee = () => {
  const items = ['VIDEO PRODUCTION', 'MOTION DESIGN', 'COMMERCIALS', 'MUSIC VIDEOS', 'DOCUMENTARIES', 'LIVE STREAMING'];
  const doubled = [...items, ...items];

  return (
    <div className="marquee">
      <div className="marquee-track">
        {doubled.map((item, i) => (
          <React.Fragment key={i}>
            <span className="marquee-item">{item}</span>
            <span className="marquee-dot">◆</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default Marquee;