// ===== Navbar scroll =====
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 50);
});

// ===== Mobile menu =====
const burger = document.getElementById('burger');
const navLinks = document.getElementById('navLinks');
burger.addEventListener('click', () => {
    burger.classList.toggle('active');
    navLinks.classList.toggle('active');
});
navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        burger.classList.remove('active');
        navLinks.classList.remove('active');
    });
});

// ===== Portfolio filters =====
const filterBtns = document.querySelectorAll('.filter-btn');
const portfolioItems = document.querySelectorAll('.portfolio-item');
filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        portfolioItems.forEach(item => {
            if (filter === 'all' || item.dataset.category === filter) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    });
});

// ===== Counter animation =====
const statNumbers = document.querySelectorAll('.stat-number');
let counted = false;
function animateCounters() {
    if (counted) return;
    const aboutSection = document.getElementById('about');
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
animateCounters();

// ===== Fade-up animation =====
const fadeEls = document.querySelectorAll('.section-label, .section-title, .service-card, .team-card, .portfolio-item, .contact-form, .contact-info, .about-text, .about-visual');
fadeEls.forEach(el => el.classList.add('fade-up'));
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
fadeEls.forEach(el => observer.observe(el));

// ===== Smooth scroll =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ===== Contact form =====
const contactForm = document.getElementById('contactForm');
contactForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const btn = contactForm.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = '✓ Надіслано!';
    btn.style.background = 'linear-gradient(135deg, #43e97b, #38f9d7)';
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
        contactForm.reset();
    }, 3000);
});