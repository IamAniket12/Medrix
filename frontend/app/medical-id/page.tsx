'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE_URL = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1`;
const API_ROOT_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PermanentCard {
  id: string;
  card_pdf_path: string;
  qr_code_data: string;
  version: number;
  generated_at: string;
  patient_name: string;
  date_of_birth?: string;
  blood_type?: string;
  gender?: string;
  emergency_contact?: { name?: string; phone?: string; relationship?: string };
  chronic_conditions?: Array<{ name: string; severity?: string }>;
  life_threatening_allergies?: Array<{ allergen: string; severity?: string }>;
}

interface DoctorSummary {
  id: string;
  file_path: string;
  pdf_url: string;
  expires_at: string;
  generated_at: string;
}

function MedicalIDCard({ card, size = 'normal' }: { card: PermanentCard; size?: 'normal' | 'large' }) {
  const lg = size === 'large';
  const w = lg ? 500 : 340;
  
  return (
    <div style={{ width: `${w}px`, aspectRatio: '1.586 / 1', borderRadius: lg ? '20px' : '14px', background: 'linear-gradient(135deg, #0b1d3a 0%, #142f5e 35%, #0e274e 65%, #061120 100%)', boxShadow: lg ? '0 48px 96px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.07)' : '0 20px 48px rgba(0,0,0,0.38), 0 0 0 1px rgba(255,255,255,0.06)', position: 'relative', overflow: 'hidden', color: 'white', flexShrink: 0, userSelect: 'none' }}>
      <div style={{ position: 'absolute', top: '-25%', right: '-8%', width: '65%', height: '65%', borderRadius: '50%', background: 'radial-gradient(circle, rgba(56,139,253,0.22) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-18%', left: '-4%', width: '48%', height: '55%', borderRadius: '50%', background: 'radial-gradient(circle, rgba(79,195,247,0.14) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(255,255,255,0.018) 23px, rgba(255,255,255,0.018) 24px)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2.5px', background: 'linear-gradient(90deg, transparent 0%, rgba(56,139,253,0.9) 30%, rgba(79,195,247,0.7) 60%, transparent 100%)' }} />
      
      <div style={{ position: 'relative', zIndex: 1, padding: lg ? '28px 32px 22px' : '18px 22px 16px', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: lg ? '9px' : '6px' }}>
            <div style={{ width: lg ? '30px' : '20px', height: lg ? '30px' : '20px', background: 'linear-gradient(135deg, #4fc3f7 0%, #1976d2 100%)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 10px rgba(79,195,247,0.5)', flexShrink: 0 }}>
              <svg viewBox="0 0 16 16" fill="white" style={{ width: lg ? '16px' : '11px', height: lg ? '16px' : '11px' }}>
                <rect x="6" y="1" width="4" height="14" rx="1" />
                <rect x="1" y="6" width="14" height="4" rx="1" />
              </svg>
            </div>
            <span style={{ fontSize: lg ? '15px' : '10px', fontWeight: 800, letterSpacing: '0.18em', color: 'rgba(255,255,255,0.92)' }}>MEDRIX</span>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '6px', padding: lg ? '4px 12px' : '2px 8px', fontSize: lg ? '11px' : '7.5px', fontWeight: 700, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.88)' }}>MEDICAL ID</div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: lg ? '14px' : '10px' }}>
          <div style={{ width: lg ? '42px' : '28px', height: lg ? '32px' : '22px', background: 'linear-gradient(135deg, #9a7b00 0%, #d4a017 25%, #f5c842 50%, #d4a017 75%, #9a7b00 100%)', borderRadius: '4px', flexShrink: 0, boxShadow: '0 2px 8px rgba(212,160,23,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: '65%', height: '60%', border: '1.5px solid rgba(0,0,0,0.22)', borderRadius: '2px' }} />
          </div>
          <div>
            <div style={{ fontSize: lg ? '21px' : '14px', fontWeight: 700, lineHeight: 1.15, color: '#ffffff' }}>{card.patient_name}</div>
            <div style={{ fontSize: lg ? '9px' : '6.5px', color: 'rgba(255,255,255,0.45)', letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: '3px' }}>Cardholder</div>
          </div>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', gap: lg ? '22px' : '14px' }}>
            {[{ label: 'Since', value: new Date(card.generated_at).getFullYear().toString() }, { label: 'Version', value: String(card.version).padStart(2, '0') }, { label: 'Status', value: 'Active', accent: true }].map(({ label, value, accent }) => (
              <div key={label}>
                <div style={{ fontSize: lg ? '9px' : '6px', color: 'rgba(255,255,255,0.4)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '3px' }}>{label}</div>
                <div style={{ fontSize: lg ? '13px' : '9px', fontWeight: 600, color: accent ? '#4fc3f7' : 'rgba(255,255,255,0.9)' }}>{value}</div>
              </div>
            ))}
          </div>
          <div style={{ background: 'linear-gradient(135deg, rgba(239,68,68,0.25), rgba(220,38,38,0.15))', border: '1px solid rgba(239,68,68,0.45)', borderRadius: '8px', padding: lg ? '5px 14px' : '3px 9px', textAlign: 'center' }}>
            <div style={{ fontSize: lg ? '7px' : '5px', color: 'rgba(255,200,200,0.7)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '1px' }}>Blood</div>
            <div style={{ fontSize: lg ? '17px' : '12px', fontWeight: 800, color: '#fca5a5', lineHeight: 1 }}>{card.blood_type || '—'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CardModal({ card, onClose, onRegenerate, regenerating }: { card: PermanentCard; onClose: () => void; onRegenerate: () => void; regenerating: boolean }) {
  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => { if (e.target === e.currentTarget) onClose(); };
  
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);
  
  const formatted = new Date(card.generated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  
  return (
    <div onClick={handleBackdrop} style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(5,12,28,0.82)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', padding: '24px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '28px', maxWidth: '560px', width: '100%' }}>
        <div style={{ width: '100%', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'rgba(255,255,255,0.8)', fontSize: '20px', lineHeight: '1' }}>×</button>
        </div>
        <MedicalIDCard card={card} size="large" />
        <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>Generated {formatted} · Version {card.version}</div>
        <div style={{ display: 'flex', gap: '12px', width: '100%' }}>
          <button onClick={onRegenerate} disabled={regenerating} style={{ width: '100%', padding: '13px', borderRadius: '10px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.8)', fontWeight: 600, fontSize: '14px', cursor: regenerating ? 'not-allowed' : 'pointer', opacity: regenerating ? 0.6 : 1 }}>{regenerating ? 'Updating…' : 'Regenerate Medical ID'}</button>
        </div>
      </div>
    </div>
  );
}

function SummaryRow({ summary }: { summary: DoctorSummary }) {
  const generated = new Date(summary.generated_at);
  const timeStr = generated.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  const dateStr = generated.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'rgba(0,0,0,0.03)', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.06)', transition: 'all 0.3s ease' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(249,115,22,0.04)'
        e.currentTarget.style.borderColor = 'rgba(249,115,22,0.25)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(0,0,0,0.03)'
        e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.1))', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <svg viewBox="0 0 24 24" fill="none" style={{ width: '20px', height: '20px' }}>
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="#3b82f6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            <polyline points="14,2 14,8 20,8" stroke="#3b82f6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: '600', color: '#1c1917' }}>Medical Summary</div>
          <div style={{ fontSize: '12px', color: '#a8a29e', marginTop: '2px' }}>{dateStr} at {timeStr}</div>
        </div>
      </div>
      <button onClick={() => window.open(`${API_ROOT_URL}${summary.pdf_url}`, '_blank')} style={{ padding: '9px 16px', borderRadius: '10px', background: 'linear-gradient(135deg, #f97316, #fb7185)', border: 'none', color: 'white', fontWeight: '600', fontSize: '13px', cursor: 'pointer', whiteSpace: 'nowrap', boxShadow: '0 4px 12px rgba(249,115,22,0.25)', transition: 'all 0.3s ease' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = '0 6px 16px rgba(249,115,22,0.35)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(249,115,22,0.25)'
        }}
      >Open PDF</button>
    </div>
  );
}

export default function MedicalIDPage() {
  const [permanentCard, setPermanentCard] = useState<PermanentCard | null>(null);
  const [summaries, setSummaries] = useState<DoctorSummary[]>([]);
  const [cardLoading, setCardLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [userId, setUserId] = useState<string | null>(() => {
    try {
      const stored = localStorage.getItem('medrix_user');
      if (stored) {
        const u = JSON.parse(stored);
        if (u?.id) return u.id;
      }
    } catch {}
    return null;
  });

  useEffect(() => {
    setAuthChecked(true);
    const onAuthChange = () => {
      try {
        const stored = localStorage.getItem('medrix_user');
        if (stored) {
          const u = JSON.parse(stored);
          if (u?.id) setUserId(u.id);
        }
      } catch {}
    };
    window.addEventListener('medrix_auth_change', onAuthChange);
    return () => window.removeEventListener('medrix_auth_change', onAuthChange);
  }, []);

  const fetchCard = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/medical-id/${userId}/card`);
      if (res.ok) setPermanentCard(await res.json());
    } catch { /* no card yet */ }
  }, [userId]);

  const fetchSummaries = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/medical-id/${userId}/summaries`);
      if (res.ok) setSummaries(await res.json());
    } catch { /* empty */ }
  }, [userId]);

  useEffect(() => { fetchCard(); fetchSummaries(); }, [fetchCard, fetchSummaries]);

  const regenerateCard = async () => {
    if (!userId) return;
    setCardLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/medical-id/${userId}/card/regenerate`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to regenerate card');
      setPermanentCard(await res.json());
    } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong'); }
    finally { setCardLoading(false); }
  };

  const generateSummary = async () => {
    if (!userId) return;
    setSummaryLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/medical-id/${userId}/summary`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expiration_minutes: 60 }),
      });
      if (!res.ok) throw new Error('Failed to generate summary');
      const data = await res.json();
      setSummaries(prev => [data, ...prev]);
    } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong'); }
    finally { setSummaryLoading(false); }
  };

  const viewEmergencyPage = () => {
    if (!permanentCard) return;
    window.open(`/medical-id/view/${userId}`, '_blank');
  };

  const router = useRouter();

  if (!authChecked) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(249,115,22,0.2)', borderTop: '3px solid #f97316', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!userId) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <div style={{ maxWidth: '440px', width: '100%', background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '24px', padding: '48px 40px', textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.07)' }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>🪪</div>
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#1c1917', marginBottom: '10px' }}>Sign in to view your Medical ID</h2>
          <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '32px', lineHeight: 1.6 }}>Your Medical ID contains sensitive health information. Please sign in to access it.</p>
          <button onClick={() => router.push('/signin')} style={{ padding: '13px 32px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 16px rgba(249,115,22,0.3)', width: '100%' }}>
            Sign In
          </button>
          <p style={{ marginTop: '16px', fontSize: '13px', color: '#a8a29e' }}>Don&apos;t have an account? <button onClick={() => router.push('/signin')} style={{ background: 'none', border: 'none', color: '#f97316', fontWeight: 700, cursor: 'pointer', fontSize: '13px', padding: 0 }}>Create one</button></p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', position: 'relative', overflow: 'hidden' }}>
        {/* Background Decorations */}
        <div style={{ position: 'absolute', top: '12%', right: '8%', width: '420px', height: '420px', background: 'radial-gradient(circle, rgba(249, 115, 22, 0.12) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(70px)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: '15%', left: '6%', width: '380px', height: '380px', background: 'radial-gradient(circle, rgba(251, 113, 133, 0.10) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(65px)', pointerEvents: 'none' }} />

        <div style={{ maxWidth: '1080px', margin: '0 auto', padding: '48px 24px 80px', position: 'relative', zIndex: 1 }}>
          <div style={{ marginBottom: '48px', textAlign: 'center' }}>
            <h1 style={{ fontSize: '42px', fontWeight: '900', letterSpacing: '-0.02em', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text', margin: 0, marginBottom: '12px' }}>Medical ID</h1>
            <p style={{ fontSize: '16px', color: '#78716c', margin: 0 }}>Your personal health identity — always secure, always accessible.</p>
          </div>

          {error && (
            <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '16px 20px', marginBottom: '32px', color: '#ef4444', fontSize: '14px', textAlign: 'center' }}>{error}</div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 1fr)', gap: '28px', alignItems: 'start' }}>
            <div style={{ background: '#ffffff', borderRadius: '20px', border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 4px 24px rgba(0,0,0,0.06)', overflow: 'hidden' }}>
              <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)' }}>
                      <svg viewBox="0 0 16 16" fill="white" style={{ width: '18px', height: '18px' }}>
                        <rect x="6" y="1" width="4" height="14" rx="1.5" />
                        <rect x="1" y="6" width="14" height="4" rx="1.5" />
                      </svg>
                    </div>
                    <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#1c1917', margin: 0 }}>Your Medical ID</h2>
                  </div>
                  <p style={{ fontSize: '14px', color: '#78716c', margin: 0 }}>Emergency card with your critical health information</p>
                </div>
                {permanentCard && (
                  <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', fontSize: '11px', fontWeight: '700', letterSpacing: '0.06em', padding: '5px 12px', borderRadius: '20px', border: '1px solid rgba(16, 185, 129, 0.4)', whiteSpace: 'nowrap', marginTop: '6px' }}>Active</span>
                )}
              </div>

              {permanentCard ? (
                <div style={{ padding: '28px 32px 32px' }}>
                  <div style={{ display: 'flex', justifyContent: 'center', padding: '32px 24px', background: 'rgba(0,0,0,0.06)', borderRadius: '16px', marginBottom: '24px' }}>
                    <MedicalIDCard card={permanentCard} size="normal" />
                  </div>
                  <button onClick={viewEmergencyPage} style={{ width: '100%', padding: '15px', borderRadius: '12px', background: 'linear-gradient(135deg, #f97316, #fb7185)', border: 'none', color: 'white', fontWeight: '700', fontSize: '15px', cursor: 'pointer', boxShadow: '0 8px 24px rgba(249,115,22,0.3)', marginBottom: '12px', letterSpacing: '0.01em', transition: 'all 0.3s ease' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)'
                      e.currentTarget.style.boxShadow = '0 12px 32px rgba(249,115,22,0.4)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(249,115,22,0.3)'
                    }}
                  >View Medical ID</button>
                  <button onClick={() => setShowModal(true)} style={{ width: '100%', padding: '13px', borderRadius: '12px', background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.09)', color: '#44403c', fontWeight: '600', fontSize: '14px', cursor: 'pointer', marginBottom: '8px', transition: 'all 0.3s ease' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(249,115,22,0.07)'
                      e.currentTarget.style.color = '#f97316'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(0,0,0,0.04)'
                      e.currentTarget.style.color = '#44403c'
                    }}
                  >View Card Details</button>
                  <button onClick={regenerateCard} disabled={cardLoading} style={{ width: '100%', padding: '13px', borderRadius: '12px', background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.09)', color: '#44403c', fontWeight: '600', fontSize: '14px', cursor: cardLoading ? 'not-allowed' : 'pointer', opacity: cardLoading ? 0.6 : 1, transition: 'all 0.3s ease' }}
                    onMouseEnter={(e) => {
                      if (!cardLoading) {
                        e.currentTarget.style.background = 'rgba(249,115,22,0.07)'
                        e.currentTarget.style.color = '#f97316'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!cardLoading) {
                        e.currentTarget.style.background = 'rgba(0,0,0,0.04)'
                        e.currentTarget.style.color = '#44403c'
                      }
                    }}
                  >{cardLoading ? 'Regenerating…' : 'Generate New Version'}</button>
                </div>
              ) : (
                <div style={{ padding: '56px 32px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
                  <div style={{ width: '80px', height: '80px', borderRadius: '20px', background: 'rgba(249,115,22,0.07)', border: '1px solid rgba(249,115,22,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg viewBox="0 0 24 24" fill="none" style={{ width: '40px', height: '40px' }}>
                      <rect x="2" y="5" width="20" height="14" rx="3" stroke="rgba(249,115,22,0.5)" strokeWidth="1.5" />
                      <rect x="5" y="9" width="6" height="4" rx="1" fill="rgba(249,115,22,0.35)" />
                      <rect x="13" y="9" width="6" height="1.5" rx="0.75" fill="rgba(249,115,22,0.35)" />
                      <rect x="13" y="12" width="4" height="1.5" rx="0.75" fill="rgba(249,115,22,0.35)" />
                    </svg>
                  </div>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: '700', color: '#1c1917', marginBottom: '8px' }}>No Medical ID yet</div>
                    <div style={{ fontSize: '14px', color: '#78716c', lineHeight: 1.5 }}>Generate your personalised card with<br />critical health information.</div>
                  </div>
                  <button onClick={regenerateCard} disabled={cardLoading} style={{ padding: '14px 32px', borderRadius: '12px', background: 'linear-gradient(135deg, #f97316, #fb7185)', border: 'none', color: 'white', fontWeight: '700', fontSize: '15px', cursor: cardLoading ? 'not-allowed' : 'pointer', boxShadow: '0 8px 24px rgba(249,115,22,0.3)', opacity: cardLoading ? 0.7 : 1, transition: 'all 0.3s ease' }}
                    onMouseEnter={(e) => {
                      if (!cardLoading) {
                        e.currentTarget.style.transform = 'translateY(-2px)'
                        e.currentTarget.style.boxShadow = '0 12px 32px rgba(249,115,22,0.4)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!cardLoading) {
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.boxShadow = '0 8px 24px rgba(249,115,22,0.3)'
                      }
                    }}
                  >{cardLoading ? 'Generating…' : 'Generate Medical ID'}</button>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ background: '#ffffff', borderRadius: '20px', border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 4px 24px rgba(0,0,0,0.06)', padding: '28px 32px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', marginBottom: '24px' }}>
                  <div style={{ width: '52px', height: '52px', borderRadius: '14px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.1))', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <svg viewBox="0 0 24 24" fill="none" style={{ width: '26px', height: '26px' }}>
                      <path d="M9 2a5 5 0 100 10A5 5 0 009 2z" stroke="#10b981" strokeWidth="1.6"/>
                      <path d="M2 20c0-3.31 3.13-6 7-6s7 2.69 7 6" stroke="#10b981" strokeWidth="1.6" strokeLinecap="round"/>
                      <path d="M19 8v6M16 11h6" stroke="#10b981" strokeWidth="1.8" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <div>
                    <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#1c1917', margin: 0, marginBottom: '8px' }}>Visiting a doctor?</h2>
                    <p style={{ fontSize: '14px', color: '#78716c', margin: 0, lineHeight: 1.6 }}>Generate a quick medical summary your doctor can review at a glance — covering medications, lab results, vitals, and an AI clinical briefing.</p>
                  </div>
                </div>
                <button onClick={generateSummary} disabled={summaryLoading} style={{ width: '100%', padding: '15px', borderRadius: '12px', background: summaryLoading ? 'rgba(0,0,0,0.07)' : 'linear-gradient(135deg, #10b981, #059669)', border: 'none', color: summaryLoading ? '#a8a29e' : 'white', fontWeight: '700', fontSize: '15px', cursor: summaryLoading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', boxShadow: summaryLoading ? 'none' : '0 8px 24px rgba(16, 185, 129, 0.4)', transition: 'all 0.3s ease' }}
                  onMouseEnter={(e) => {
                    if (!summaryLoading) {
                      e.currentTarget.style.transform = 'translateY(-2px)'
                      e.currentTarget.style.boxShadow = '0 12px 32px rgba(16, 185, 129, 0.5)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!summaryLoading) {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(16, 185, 129, 0.4)'
                    }
                  }}
                >
                  {summaryLoading ? 'Generating summary…' : 'Generate Quick Summary'}
                </button>
                <p style={{ fontSize: '12px', color: '#a8a29e', textAlign: 'center', margin: '12px 0 0', lineHeight: 1.5 }}>AI-powered · Takes ~30 seconds · Exported as PDF</p>
              </div>

              {summaries.length > 0 && (
                <div style={{ background: '#ffffff', borderRadius: '20px', border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 4px 24px rgba(0,0,0,0.06)', padding: '24px 28px' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: '700', color: '#1c1917', margin: '0 0 16px', letterSpacing: '0.02em' }}>Recent Summaries</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {summaries.slice(0, 5).map(s => <SummaryRow key={s.id} summary={s} />)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showModal && permanentCard && (
        <CardModal card={permanentCard} onClose={() => setShowModal(false)} onRegenerate={regenerateCard} regenerating={cardLoading} />
      )}
    </>
  );
}
