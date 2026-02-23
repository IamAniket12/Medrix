'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';

export default function Home() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  const [cardName, setCardName] = useState('Aniket Dixit');

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Read signed-in user from localStorage
    const updateCardName = () => {
      try {
        const stored = localStorage.getItem('medrix_user');
        if (stored) {
          const u = JSON.parse(stored);
          if (u?.name) setCardName(u.name);
        }
      } catch {}
    };
    updateCardName();
    window.addEventListener('medrix_auth_change', updateCardName);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('medrix_auth_change', updateCardName);
    };
  }, []);

  const features = [
    { icon: '🏥', title: 'Smart Document Processing', description: 'AI-powered extraction of medical data from any document format', accent: '#f97316', accentBg: 'rgba(249,115,22,0.08)' },
    { icon: '💳', title: 'Emergency Medical ID', description: 'Instant access to critical health information when it matters most', accent: '#fb7185', accentBg: 'rgba(251,113,133,0.08)' },
    { icon: '🤖', title: 'MediBot — Ask AI', description: 'Ask questions and get instant answers from your complete medical history', accent: '#a78bfa', accentBg: 'rgba(167,139,250,0.08)' },
    { icon: '📊', title: 'Complete History', description: 'All your medical documents organized and accessible in one place', accent: '#34d399', accentBg: 'rgba(52,211,153,0.08)' },
  ];

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: '8%', right: '12%', width: '520px', height: '520px', background: 'radial-gradient(circle, rgba(249,115,22,0.12) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(70px)', transform: `translate(${mousePosition.x * 0.012}px, ${mousePosition.y * 0.012}px)`, transition: 'transform 0.4s ease-out', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '12%', left: '8%', width: '420px', height: '420px', background: 'radial-gradient(circle, rgba(251,113,133,0.1) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(60px)', transform: `translate(${-mousePosition.x * 0.01}px, ${-mousePosition.y * 0.01}px)`, transition: 'transform 0.4s ease-out', pointerEvents: 'none' }} />

      {/* Hero */}
      <div style={{ maxWidth: '1360px', margin: '0 auto', padding: '0 32px', position: 'relative', zIndex: 1 }}>
        <div style={{ paddingTop: '100px', paddingBottom: '80px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '80px', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.22)', padding: '7px 16px', borderRadius: '100px', marginBottom: '28px' }}>
              <div style={{ width: '7px', height: '7px', background: '#f97316', borderRadius: '50%', animation: 'pulse 2s infinite' }} />
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#f97316', letterSpacing: '0.07em' }}>AI-POWERED HEALTHCARE</span>
            </div>
            <h1 style={{ fontSize: '68px', fontWeight: 900, lineHeight: 1.08, marginBottom: '24px', letterSpacing: '-0.025em' }}>
              <span style={{ color: '#1c1917' }}>Your Medical</span><br />
              <span style={{ background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>History, Unified</span>
            </h1>
            <p style={{ fontSize: '19px', color: '#78716c', lineHeight: 1.75, marginBottom: '40px', maxWidth: '520px' }}>
              Transform scattered medical documents into a comprehensive, AI-organized health record. Emergency-ready. Always accessible.
            </p>
            <div style={{ display: 'flex', gap: '14px', marginBottom: '52px' }}>
              <Link href="/upload" style={{ textDecoration: 'none' }}>
                <button
                  style={{ padding: '15px 32px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '14px', color: 'white', fontSize: '16px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 8px 28px rgba(249,115,22,0.3)', transition: 'all 0.3s ease', display: 'flex', alignItems: 'center', gap: '8px' }}
                  onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 12px 36px rgba(249,115,22,0.38)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 28px rgba(249,115,22,0.3)'; }}>
                  Get Started
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10m0 0L9 4m4 4l-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </button>
              </Link>
              <Link href="/medical-id" style={{ textDecoration: 'none' }}>
                <button
                  style={{ padding: '15px 32px', background: 'white', border: '1.5px solid rgba(249,115,22,0.25)', borderRadius: '14px', color: '#78716c', fontSize: '16px', fontWeight: 600, cursor: 'pointer', transition: 'all 0.3s ease', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.5)'; e.currentTarget.style.color = '#f97316'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.25)'; e.currentTarget.style.color = '#78716c'; }}>
                  View Medical ID
                </button>
              </Link>
            </div>

          </div>

          {/* Card */}
          <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ position: 'absolute', inset: '-30px', background: 'radial-gradient(ellipse, rgba(249,115,22,0.16) 0%, rgba(251,113,133,0.1) 50%, transparent 70%)', filter: 'blur(30px)', borderRadius: '32px', opacity: isHovered ? 1 : 0.6, transition: 'opacity 0.6s ease' }} />
            <div
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              style={{ position: 'relative', transform: isHovered ? 'scale(1.04) rotateY(4deg) rotateX(2deg)' : 'scale(1)', transition: 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)', transformStyle: 'preserve-3d' }}>
              <div style={{ position: 'relative', width: '420px', height: '265px', background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0c1a2e 100%)', borderRadius: '22px', padding: '26px 28px', boxShadow: '0 32px 64px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: '-15%', right: '-5%', width: '55%', height: '60%', background: 'radial-gradient(circle, rgba(249,115,22,0.18) 0%, transparent 70%)', borderRadius: '50%' }} />
                <div style={{ position: 'absolute', bottom: '-12%', left: '-4%', width: '45%', height: '55%', background: 'radial-gradient(circle, rgba(251,113,133,0.12) 0%, transparent 70%)', borderRadius: '50%' }} />
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: 'linear-gradient(90deg, transparent, rgba(249,115,22,0.7), rgba(251,113,133,0.5), transparent)' }} />
                <div style={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                      <div style={{ width: '28px', height: '28px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', borderRadius: '7px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 10px rgba(249,115,22,0.4)' }}>
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="white"><rect x="6" y="1" width="4" height="14" rx="1.5"/><rect x="1" y="6" width="14" height="4" rx="1.5"/></svg>
                      </div>
                      <span style={{ fontSize: '14px', fontWeight: 900, letterSpacing: '0.15em', color: 'white' }}>MEDRIX</span>
                    </div>
                    <div style={{ background: 'rgba(239,68,68,0.18)', border: '1px solid rgba(239,68,68,0.35)', borderRadius: '6px', padding: '4px 10px', fontSize: '9px', fontWeight: 700, color: '#fca5a5', letterSpacing: '0.05em' }}>EMERGENCY ID</div>
                  </div>
                  <div style={{ width: '44px', height: '33px', background: 'linear-gradient(135deg, #9a7b00 0%, #d4a017 25%, #f5c842 50%, #d4a017 75%, #9a7b00 100%)', borderRadius: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ width: '68%', height: '58%', border: '1.5px solid rgba(0,0,0,0.15)', borderRadius: '2px' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: '22px', fontWeight: 700, color: 'white', marginBottom: '7px' }}>{cardName}</div>
                    <div style={{ display: 'flex', gap: '20px', fontSize: '12px', color: 'rgba(255,255,255,0.55)' }}>
                      <div><div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '2px' }}>Blood Type</div><div style={{ fontSize: '15px', fontWeight: 700, color: '#fda4af' }}>O+</div></div>
                      <div><div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '2px' }}>DOB</div><div style={{ fontSize: '15px', fontWeight: 600, color: 'rgba(255,255,255,0.88)' }}>03/15/1985</div></div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>VALID SINCE 2024</div>
                    <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>ID: DEMO-001</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features */}
      <div style={{ background: 'rgba(255,255,255,0.55)', backdropFilter: 'blur(12px)', borderTop: '1px solid rgba(249,115,22,0.1)', padding: '96px 32px' }}>
        <div style={{ maxWidth: '1360px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <h2 style={{ fontSize: '42px', fontWeight: 800, color: '#1c1917', marginBottom: '14px', letterSpacing: '-0.02em' }}>Everything You Need</h2>
            <p style={{ fontSize: '17px', color: '#78716c', maxWidth: '540px', margin: '0 auto', lineHeight: 1.7 }}>Comprehensive healthcare management powered by cutting-edge AI technology</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '18px' }}>
            {features.map((feature, i) => (
              <Link key={i} href={i === 1 ? '/medical-id' : i === 0 ? '/upload' : i === 2 ? '/ask' : '/documents'} style={{ textDecoration: 'none' }}>
                <div
                  style={{ background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '20px', padding: '32px', transition: 'all 0.3s ease', cursor: 'pointer', position: 'relative', overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-5px)'; e.currentTarget.style.borderColor = `${feature.accent}55`; e.currentTarget.style.boxShadow = `0 12px 36px ${feature.accent}14`; }}
                  onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.04)'; }}>
                  <div style={{ position: 'absolute', top: '-40px', right: '-40px', width: '160px', height: '160px', background: `radial-gradient(circle, ${feature.accentBg} 0%, transparent 70%)`, borderRadius: '50%', pointerEvents: 'none' }} />
                  <div style={{ fontSize: '42px', marginBottom: '16px' }}>{feature.icon}</div>
                  <h3 style={{ fontSize: '21px', fontWeight: 700, color: '#1c1917', marginBottom: '10px' }}>{feature.title}</h3>
                  <p style={{ fontSize: '15px', color: '#78716c', lineHeight: 1.7, margin: 0 }}>{feature.description}</p>
                  <div style={{ marginTop: '18px', display: 'inline-flex', alignItems: 'center', gap: '5px', color: feature.accent, fontSize: '13px', fontWeight: 700 }}>
                    Learn more
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8h10m0 0L9 4m4 4l-4 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.9); } }
      `}</style>
    </div>
  );
}
