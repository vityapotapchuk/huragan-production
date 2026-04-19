// ===== Preloader =====
const preloader = document.getElementById('preloader');
const progressBar = document.getElementById('preloaderProgress');
const percentEl = document.getElementById('preloaderPercent');
let progress = 0;
const preloaderInterval = setInterval(() => {
    progress += Math.random() * 15 + 5;
    if (progress >= 100) {
        progress = 100;
        clearInterval(preloaderInterval);
        setTimeout(() => {
            preloader.classList.add('hidden');
            document.body.style.overflow = '';
            initRevealAnimations();
        }, 400);
    }
    progressBar.style.width = progress + '%';
    percentEl.textContent = Math.round(progress) + '%';
}, 150);
document.body.style.overflow = 'hidden';

// ===== Custom Cursor =====
const cursor = document.getElementById('cursor');
const follower = document.getElementById('cursorFollower');
let mouseX = 0, mouseY = 0, followerX = 0, followerY = 0;

document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    cursor.style.left = mouseX + 'px';
    cursor.style.top = mouseY + 'px';
});

function animateFollower() {
    followerX += (mouseX - followerX) * 0.12;
    followerY += (mouseY - followerY) * 0.12;
    follower.style.left = followerX + 'px';
    follower.style.top = followerY + 'px';
    requestAnimationFrame(animateFollower);
}
animateFollower();

// Cursor hover states
const hoverTargets = document.querySelectorAll('a, button, .work-thumb, .service-row, .stat-card, .contact-card');
hoverTargets.forEach(el => {
    el.addEventListener('mouseenter', () => {
        cursor.classList.add('hovering');
        follower.classList.add('hovering');
    });
    el.addEventListener('mouseleave', () => {
        cursor.classList.remove('hovering');
        follower.classList.remove('hovering');
    });
});

// ===== Navbar =====
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
});

// ===== Mobile Menu =====
const burger = document.getElementById('navBurger');
const mobileMenu = document.getElementById('mobileMenu');
burger.addEventListener('click', () => {
    burger.classList.toggle('active');
    mobileMenu.classList.toggle('active');
});
document.querySelectorAll('.mobile-link, .mobile-cta').forEach(link => {
    link.addEventListener('click', () => {
        burger.classList.remove('active');
        mobileMenu.classList.remove('active');
    });
});

// ===== Smooth Scroll =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ===== Reveal Animations =====
function initRevealAnimations() {
    const reveals = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 80);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(el => observer.observe(el));
}

// ===== Portfolio Filters =====
const filterBtns = document.querySelectorAll('.filter-btn');
const workItems = document.querySelectorAll('.work-item');
filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        workItems.forEach(item => {
            if (filter === 'all' || item.dataset.category === filter) {
                item.classList.remove('hidden');
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    item.style.transition = 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
                    item.style.opacity = '1';
                    item.style.transform = 'translateY(0)';
                }, 50);
            } else {
                item.classList.add('hidden');
            }
        });
    });
});

// ===== Counter Animation =====
const statNumbers = document.querySelectorAll('.stat-number');
let counted = false;
function animateCounters() {
    if (counted) return;
    const aboutSection = document.getElementById('about');
    if (!aboutSection) return;
    const rect = aboutSection.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.8) {
        counted = true;
        statNumbers.forEach(num => {
            const target = parseInt(num.dataset.target);
            const duration = 2000;
            const start = performance.now();
            function update(now) {
                const elapsed = now - start;
                const progress = Math.min(elapsed / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                num.textContent = Math.round(target * eased);
                if (progress < 1) requestAnimationFrame(update);
            }
            requestAnimationFrame(update);
        });
    }
}
window.addEventListener('scroll', animateCounters);

// ===== Contact Form =====
const contactForm = document.getElementById('contactForm');
contactForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const btn = contactForm.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = '✓ Sent!';
    btn.style.background = 'var(--accent-2)';
    btn.style.color = 'var(--text)';
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
        btn.style.color = '';
        contactForm.reset();
    }, 3000);
});

// ===== Hero Video Placeholder Animation =====
const heroVideo = document.getElementById('heroVideo');
if (heroVideo) {
    let hue = 0;
    function animateHeroBg() {
        hue += 0.2;
        const x = 50 + Math.sin(hue * 0.01) * 20;
        const y = 50 + Math.cos(hue * 0.013) * 15;
        heroVideo.style.background = `
            radial-gradient(ellipse 80% 70% at ${x}% ${y}%, rgba(108,92,231,0.1) 0%, transparent 50%),
            radial-gradient(ellipse 60% 50% at ${100-x}% ${100-y}%, rgba(0,206,201,0.07) 0%, transparent 50%),
            radial-gradient(ellipse 50% 40% at ${y}% ${x}%, rgba(253,121,168,0.05) 0%, transparent 50%)
        `;
        requestAnimationFrame(animateHeroBg);
    }
    animateHeroBg();
}