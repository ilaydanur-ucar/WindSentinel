import { useState, useEffect } from 'react';
import { useLanguage } from '../hooks/useLanguage';

/* Spinning blades only - no tower */
const WindTurbineSVG = ({ size = 80, opacity = 0.10, speed = 8 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" opacity={opacity}>
    <g style={{ transformOrigin: '50px 50px', animation: `rotate ${speed}s linear infinite` }}>
      <path d="M50 50 L47 8 Q50 2 53 8 Z" fill="#1a3a5c"/>
      <path d="M50 50 L86 72 Q88 67 84 65 Z" fill="#1a3a5c"/>
      <path d="M50 50 L14 72 Q12 67 16 65 Z" fill="#1a3a5c"/>
    </g>
    <circle cx="50" cy="50" r="4.5" fill="#1a3a5c"/>
  </svg>
);

const smoothScroll = (e, targetId) => {
  e.preventDefault();
  const el = document.getElementById(targetId);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

export default function Landing({ onShowLogin }) {
  const { t, lang, setLang } = useLanguage();
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isVisible, setIsVisible] = useState({});
  const [scrolled, setScrolled] = useState(false);

  const slides = [
    { title: t('slide1Title'), highlight: t('slide1Highlight'), desc: t('slide1Desc') },
    { title: t('slide2Title'), highlight: t('slide2Highlight'), desc: t('slide2Desc') },
    { title: t('slide3Title'), highlight: t('slide3Highlight'), desc: t('slide3Desc') },
  ];

  const features = [
    {
      icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>,
      title: t('feat1Title'), desc: t('feat1Desc'),
    },
    {
      icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>,
      title: t('feat2Title'), desc: t('feat2Desc'),
    },
    {
      icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round"><path d="M18 20V10M12 20V4M6 20v-6" /></svg>,
      title: t('feat3Title'), desc: t('feat3Desc'),
    },
    {
      icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
      title: t('feat4Title'), desc: t('feat4Desc'),
    },
  ];

  const audiences = [
    {
      icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="1.8" strokeLinecap="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
      title: t('aud1Title'), desc: t('aud1Desc'),
    },
    {
      icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="1.8" strokeLinecap="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>,
      title: t('aud2Title'), desc: t('aud2Desc'),
    },
    {
      icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="1.8" strokeLinecap="round"><path d="M12 20V10M18 20V4M6 20v-4"/><path d="M2 20h20"/></svg>,
      title: t('aud3Title'), desc: t('aud3Desc'),
    },
    {
      icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1d6fb8" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>,
      title: t('aud4Title'), desc: t('aud4Desc'),
    },
  ];

  const stats = [
    { value: '5', label: t('statTurbines'), suffix: '' },
    { value: '<12', label: t('statInference'), suffix: 'ms' },
    { value: '24', label: t('statLeadTime'), suffix: lang === 'tr' ? ' saat' : 'h' },
    { value: '0.70', label: t('statF1'), suffix: '' },
  ];

  useEffect(() => {
    const timer = setInterval(() => setCurrentSlide((prev) => (prev + 1) % slides.length), 5000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) setIsVisible((prev) => ({ ...prev, [entry.target.id]: true }));
      }),
      { threshold: 0.1 }
    );
    document.querySelectorAll('.animate-section').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing">
      {/* Floating spinning wind turbines */}
      <div className="wind-turbines-bg">
        <div className="wt-float wt-1"><WindTurbineSVG size={70} opacity={0.08} speed={10} /></div>
        <div className="wt-float wt-2"><WindTurbineSVG size={50} opacity={0.07} speed={14} /></div>
        <div className="wt-float wt-3"><WindTurbineSVG size={90} opacity={0.06} speed={8} /></div>
        <div className="wt-float wt-4"><WindTurbineSVG size={60} opacity={0.08} speed={12} /></div>
        <div className="wt-float wt-5"><WindTurbineSVG size={45} opacity={0.07} speed={16} /></div>
        <div className="wt-float wt-6"><WindTurbineSVG size={55} opacity={0.07} speed={11} /></div>
        <div className="wt-float wt-7"><WindTurbineSVG size={75} opacity={0.06} speed={9} /></div>
        <div className="wt-float wt-8"><WindTurbineSVG size={40} opacity={0.08} speed={15} /></div>
      </div>

      {/* NAV */}
      <nav className={`landing-nav ${scrolled ? 'nav-scrolled' : ''}`}>
        <div className="landing-logo">
          <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M50 5C28 5 15 18 15 35v25c0 10 5 19 14 24l18 10c2 1 4 1 6 0l18-10c9-5 14-14 14-24V35C85 18 72 5 50 5z" fill="none" stroke="#1d6fb8" strokeWidth="5" strokeLinejoin="round"/>
            <circle cx="50" cy="52" r="5" fill="#1d6fb8"/>
            <line x1="50" y1="47" x2="50" y2="20" stroke="#1d6fb8" strokeWidth="6" strokeLinecap="round"/>
            <line x1="54" y1="55" x2="74" y2="72" stroke="#1d6fb8" strokeWidth="6" strokeLinecap="round"/>
            <line x1="46" y1="55" x2="26" y2="72" stroke="#1d6fb8" strokeWidth="6" strokeLinecap="round"/>
          </svg>
          <div>
            <span className="landing-brand">WIND <span>SENTINEL</span></span>
            <span className="landing-tagline">{t('landingSubtitle')}</span>
          </div>
        </div>
        <div className="landing-nav-links">
          <a href="#features" onClick={(e) => smoothScroll(e, 'features')}>{t('navFeatures')}</a>
          <a href="#audience" onClick={(e) => smoothScroll(e, 'audience')}>{t('navAudience')}</a>
          <a href="#how" onClick={(e) => smoothScroll(e, 'how')}>{t('navHow')}</a>
          <a href="#about" onClick={(e) => smoothScroll(e, 'about')}>{t('navAbout')}</a>
        </div>
        <div className="landing-nav-actions">
          <button className="lang-toggle-landing" onClick={() => setLang(lang === 'tr' ? 'en' : 'tr')}>
            {lang === 'tr' ? '🇬🇧 EN' : '🇹🇷 TR'}
          </button>
          <button className="btn-landing-outline" onClick={onShowLogin}>{t('signIn')}</button>
          <button className="btn-landing-primary" onClick={onShowLogin}>{t('getDemo')}</button>
        </div>
      </nav>

      {/* HERO SLIDER */}
      <section className="hero-section">
        <div className="hero-bg-pattern"></div>
        <div className="wind-lines">
          {[...Array(3)].map((_, i) => <div key={i} className={`wind-line wl-${i + 1}`}></div>)}
        </div>
        {slides.map((slide, i) => (
          <div key={i} className={`hero-slide ${i === currentSlide ? 'active' : ''}`}>
            <div className="hero-content">
              <div className="hero-badge">
                <span className="hero-badge-dot"></span>
                {t('heroBadge')}
              </div>
              <h1>{slide.title} <span>{slide.highlight}</span></h1>
              <p>{slide.desc}</p>
              <div className="hero-btns">
                <button className="btn-landing-primary btn-lg" onClick={onShowLogin}>
                  {t('goToPanel')}
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
                <a href="#how" onClick={(e) => smoothScroll(e, 'how')} className="btn-landing-ghost btn-lg">{t('howItWorks')}</a>
              </div>
            </div>
          </div>
        ))}
        <div className="hero-dots">
          {slides.map((_, i) => <button key={i} className={`hero-dot ${i === currentSlide ? 'active' : ''}`} onClick={() => setCurrentSlide(i)} />)}
        </div>
      </section>

      {/* STATS BAR */}
      <section className="stats-section">
        {stats.map((s, i) => (
          <div key={i} className="stat-card">
            <div className="stat-value">{s.value}<span>{s.suffix}</span></div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </section>

      {/* FEATURES */}
      <section id="features" className="animate-section landing-section">
        <div className={`section-inner ${isVisible['features'] ? 'visible' : ''}`}>
          <div className="section-header">
            <span className="section-badge">{t('navFeatures')}</span>
            <h2>{t('featuresTitle')}</h2>
            <p>{t('featuresSubtitle')}</p>
          </div>
          <div className="features-grid">
            {features.map((f, i) => (
              <div key={i} className="feature-card">
                <div className="feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AUDIENCE */}
      <section id="audience" className="animate-section landing-section alt-bg">
        <div className={`section-inner ${isVisible['audience'] ? 'visible' : ''}`}>
          <div className="section-header">
            <span className="section-badge">{t('navAudience')}</span>
            <h2>{t('audienceTitle')}</h2>
            <p>{t('audienceSubtitle')}</p>
          </div>
          <div className="audience-grid">
            {audiences.map((a, i) => (
              <div key={i} className="audience-card">
                <div className="audience-icon">{a.icon}</div>
                <h3>{a.title}</h3>
                <p>{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="animate-section landing-section">
        <div className={`section-inner ${isVisible['how'] ? 'visible' : ''}`}>
          <div className="section-header">
            <span className="section-badge">{t('navHow')}</span>
            <h2>{t('howTitle')}</h2>
            <p>{t('howSubtitle')}</p>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <h3>{t('step1Title')}</h3>
              <p>{t('step1Desc')}</p>
              <span className="step-tag blue">{t('step1Tag')}</span>
            </div>
            <div className="step-connector">
              <svg width="40" height="24" viewBox="0 0 40 24" fill="none">
                <path d="M0 12h36M30 6l6 6-6 6" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="step-card">
              <div className="step-number">02</div>
              <h3>{t('step2Title')}</h3>
              <p>{t('step2Desc')}</p>
              <span className="step-tag amber">{t('step2Tag')}</span>
            </div>
            <div className="step-connector">
              <svg width="40" height="24" viewBox="0 0 40 24" fill="none">
                <path d="M0 12h36M30 6l6 6-6 6" stroke="#1d6fb8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="step-card">
              <div className="step-number">03</div>
              <h3>{t('step3Title')}</h3>
              <p>{t('step3Desc')}</p>
              <span className="step-tag green">{t('step3Tag')}</span>
            </div>
          </div>
        </div>
      </section>

      {/* ABOUT */}
      <section id="about" className="animate-section landing-section alt-bg">
        <div className={`section-inner ${isVisible['about'] ? 'visible' : ''}`}>
          <div className="section-header">
            <span className="section-badge">{t('navAbout')}</span>
            <h2>{t('aboutTitle')}</h2>
          </div>
          <div className="about-grid">
            <div className="about-card">
              <h3>{t('missionTitle')}</h3>
              <p>{t('missionText')}</p>
            </div>
            <div className="about-card">
              <h3>{t('visionTitle')}</h3>
              <p>{t('visionText')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="cta-turbine">
          <svg width="120" height="120" viewBox="0 0 100 100" fill="none" opacity="0.1">
            <circle cx="50" cy="50" r="5" fill="white"/>
            <line x1="50" y1="45" x2="50" y2="10" stroke="white" strokeWidth="6" strokeLinecap="round"/>
            <line x1="54" y1="53" x2="82" y2="72" stroke="white" strokeWidth="6" strokeLinecap="round"/>
            <line x1="46" y1="53" x2="18" y2="72" stroke="white" strokeWidth="6" strokeLinecap="round"/>
          </svg>
        </div>
        <div className="cta-inner">
          <h2>{t('ctaTitle')}</h2>
          <p>{t('ctaSubtitle')}</p>
          <button className="btn-landing-primary btn-lg" onClick={onShowLogin}>
            {t('getDemo')}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="landing-footer">
        <div className="footer-left">
          <span className="landing-brand sm">WIND <span>SENTINEL</span></span>
          <span className="footer-copy">{t('footerText')}</span>
        </div>
        <span className="footer-copy">&copy; 2026 WIND Sentinel</span>
      </footer>
    </div>
  );
}
