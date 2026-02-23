'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function SignInPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    // Redirect if already signed in
    const user = localStorage.getItem('medrix_user');
    if (user) router.replace('/');
  }, [router]);

  useEffect(() => {
    const handler = (e: MouseEvent) => setMousePos({ x: e.clientX, y: e.clientY });
    window.addEventListener('mousemove', handler);
    return () => window.removeEventListener('mousemove', handler);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) { setError('Please enter your email.'); return; }
    if (mode === 'register' && !name.trim()) { setError('Please enter your name.'); return; }

    setLoading(true);
    try {
      const endpoint = mode === 'login'
        ? 'http://localhost:8000/api/v1/users/login'
        : 'http://localhost:8000/api/v1/users/register';

      const body = mode === 'login'
        ? { email: email.trim() }
        : { email: email.trim(), name: name.trim() };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        // If login fails with 404, suggest registering
        if (res.status === 404) {
          setError('');
          setMode('register');
          setError('No account found. Please fill in your name to create one.');
          setLoading(false);
          return;
        }
        throw new Error(data.detail || 'Something went wrong.');
      }

      // Save user to localStorage
      localStorage.setItem('medrix_user', JSON.stringify(data));
      window.dispatchEvent(new Event('medrix_auth_change'));
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background orbs */}
      <div style={{
        position: 'fixed', top: '-20%', right: '-10%', width: '600px', height: '600px',
        background: 'radial-gradient(circle, rgba(249,115,22,0.13) 0%, transparent 70%)',
        borderRadius: '50%', filter: 'blur(70px)', pointerEvents: 'none',
        transform: `translate(${mousePos.x * 0.01}px, ${mousePos.y * 0.01}px)`,
        transition: 'transform 0.5s ease-out',
      }} />
      <div style={{
        position: 'fixed', bottom: '-20%', left: '-10%', width: '500px', height: '500px',
        background: 'radial-gradient(circle, rgba(251,113,133,0.1) 0%, transparent 70%)',
        borderRadius: '50%', filter: 'blur(60px)', pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: '460px', position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <Link href="/" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '44px', height: '44px',
              background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
              borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(249,115,22,0.3)',
            }}>
              <svg width="22" height="22" viewBox="0 0 16 16" fill="white">
                <rect x="6" y="1" width="4" height="14" rx="1.5"/>
                <rect x="1" y="6" width="14" height="4" rx="1.5"/>
              </svg>
            </div>
            <span style={{
              fontSize: '28px', fontWeight: 900,
              background: 'linear-gradient(135deg, #1c1917 0%, #f97316 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>Medrix</span>
          </Link>
          <p style={{ marginTop: '10px', fontSize: '15px', color: '#a8a29e' }}>
            Your medical history, unified
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: '#ffffff',
          border: '1.5px solid rgba(0,0,0,0.06)',
          borderRadius: '24px',
          padding: '40px',
          boxShadow: '0 8px 40px rgba(0,0,0,0.07)',
        }}>
          {/* Mode toggle */}
          <div style={{
            display: 'flex', background: 'rgba(0,0,0,0.04)',
            borderRadius: '12px', padding: '4px', marginBottom: '32px', gap: '4px',
          }}>
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(''); }}
                style={{
                  flex: 1, padding: '10px', borderRadius: '9px', border: 'none',
                  fontSize: '14px', fontWeight: 700, cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  background: mode === m ? '#ffffff' : 'transparent',
                  color: mode === m ? '#f97316' : '#78716c',
                  boxShadow: mode === m ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
                }}
              >
                {m === 'login' ? '🔑 Sign In' : '✨ Create Account'}
              </button>
            ))}
          </div>

          <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#1c1917', marginBottom: '6px' }}>
            {mode === 'login' ? 'Welcome back' : 'Create your account'}
          </h1>
          <p style={{ fontSize: '14px', color: '#78716c', marginBottom: '28px' }}>
            {mode === 'login'
              ? 'Enter your email to access your health records.'
              : 'Fill in your details to get started.'}
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {mode === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#44403c', marginBottom: '6px' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  autoFocus
                  style={{
                    width: '100%', padding: '12px 16px',
                    border: '1.5px solid rgba(0,0,0,0.1)', borderRadius: '12px',
                    fontSize: '15px', color: '#1c1917', background: '#fafaf9',
                    outline: 'none', transition: 'border-color 0.2s',
                    boxSizing: 'border-box',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.5)'; e.currentTarget.style.background = '#fff'; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.1)'; e.currentTarget.style.background = '#fafaf9'; }}
                />
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#44403c', marginBottom: '6px' }}>
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoFocus={mode === 'login'}
                style={{
                  width: '100%', padding: '12px 16px',
                  border: '1.5px solid rgba(0,0,0,0.1)', borderRadius: '12px',
                  fontSize: '15px', color: '#1c1917', background: '#fafaf9',
                  outline: 'none', transition: 'border-color 0.2s',
                  boxSizing: 'border-box',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.5)'; e.currentTarget.style.background = '#fff'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(0,0,0,0.1)'; e.currentTarget.style.background = '#fafaf9'; }}
              />
            </div>

            {error && (
              <div style={{
                padding: '12px 16px',
                background: 'rgba(239,68,68,0.06)',
                border: '1px solid rgba(239,68,68,0.2)',
                borderRadius: '10px',
                fontSize: '13px',
                color: '#dc2626',
                fontWeight: 500,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '14px',
                background: loading ? 'rgba(249,115,22,0.5)' : 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
                border: 'none', borderRadius: '12px',
                color: 'white', fontSize: '15px', fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: loading ? 'none' : '0 6px 20px rgba(249,115,22,0.3)',
                transition: 'all 0.2s ease',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                marginTop: '8px',
              }}
              onMouseEnter={(e) => { if (!loading) e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              {loading ? (
                <>
                  <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.4)', borderTop: '2px solid white', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  {mode === 'login' ? 'Signing in…' : 'Creating account…'}
                </>
              ) : (
                mode === 'login' ? 'Sign In →' : 'Create Account →'
              )}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '13px', color: '#a8a29e' }}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
              style={{ background: 'none', border: 'none', color: '#f97316', fontWeight: 700, cursor: 'pointer', fontSize: '13px', padding: 0 }}
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
