'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';

const API_BASE_URL = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1`;

interface EmergencyContact {
  name?: string;
  phone?: string;
  relationship?: string;
}

interface EmergencyInfo {
  patient_name: string;
  age?: number;
  blood_type?: string;
  gender?: string;
  emergency_contact?: EmergencyContact;
  critical_conditions: string[];
  life_threatening_allergies: string[];
  emergency_notes?: string;
  last_updated: string;
}

export default function EmergencyViewPage() {
  const params = useParams();
  const userId = params?.userId as string;
  const [info, setInfo] = useState<EmergencyInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchEmergencyInfo = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE_URL}/medical-id/${userId}/emergency-info`);
        
        if (!res.ok) {
          throw new Error('Unable to retrieve emergency information');
        }
        
        const data = await res.json();
        setInfo(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load emergency information');
        console.error('Emergency info fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchEmergencyInfo();
  }, [userId]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0d47a1 0%, #1565c0 100%)' }}>
        <div style={{ textAlign: 'center', color: 'white' }}>
          <div style={{ width: '48px', height: '48px', border: '4px solid rgba(255,255,255,0.3)', borderTop: '4px solid white', borderRadius: '50%', margin: '0 auto 16px', animation: 'spin 1s linear infinite' }}></div>
          <div style={{ fontSize: '16px', fontWeight: 600 }}>Loading Emergency Information...</div>
        </div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error || !info) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f3f4f6', padding: '24px' }}>
        <div style={{ maxWidth: '500px', width: '100%', background: 'white', borderRadius: '16px', padding: '32px', textAlign: 'center', boxShadow: '0 10px 40px rgba(0,0,0,0.1)' }}>
          <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: '#fee2e2', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <svg viewBox="0 0 24 24" fill="none" style={{ width: '32px', height: '32px' }}>
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#111827', marginBottom: '8px' }}>Unable to Load Information</h2>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '0' }}>{error || 'Emergency information not available for this user.'}</p>
        </div>
      </div>
    );
  }

  const lastUpdated = new Date(info.last_updated).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0d47a1 0%, #1565c0 50%, #1976d2 100%)', padding: '32px 16px' }}>
      {/* Header */}
      <div style={{ maxWidth: '800px', margin: '0 auto 24px', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)', padding: '12px 24px', borderRadius: '50px', border: '1px solid rgba(255,255,255,0.2)', marginBottom: '16px' }}>
          <svg viewBox="0 0 16 16" fill="white" style={{ width: '20px', height: '20px' }}>
            <rect x="6" y="1" width="4" height="14" rx="1.5" />
            <rect x="1" y="6" width="14" height="4" rx="1.5" />
          </svg>
          <span style={{ fontSize: '15px', fontWeight: 800, letterSpacing: '0.12em', color: 'white' }}>MEDRIX</span>
        </div>
        <h1 style={{ fontSize: '32px', fontWeight: 800, color: 'white', marginBottom: '8px', letterSpacing: '-0.02em' }}>🚨 Emergency Medical ID</h1>
        <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)', margin: 0 }}>Critical patient information for first responders</p>
      </div>

      {/* Main Card */}
      <div style={{ maxWidth: '800px', margin: '0 auto', background: 'white', borderRadius: '20px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)', overflow: 'hidden' }}>
        
        {/* Patient Header */}
        <div style={{ background: 'linear-gradient(135deg, #b71c1c 0%, #d32f2f 100%)', padding: '28px 32px', color: 'white' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: '28px', fontWeight: 800, marginBottom: '4px', letterSpacing: '-0.01em' }}>{info.patient_name}</h2>
              <div style={{ display: 'flex', gap: '16px', fontSize: '14px', color: 'rgba(255,255,255,0.9)' }}>
                {info.age && <span>Age: {info.age}</span>}
                {info.gender && <span>Gender: {info.gender.charAt(0).toUpperCase() + info.gender.slice(1)}</span>}
              </div>
            </div>
            {info.blood_type && (
              <div style={{ background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', borderRadius: '12px', padding: '12px 20px', textAlign: 'center', minWidth: '100px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '2px', opacity: 0.9 }}>BLOOD TYPE</div>
                <div style={{ fontSize: '32px', fontWeight: 900, lineHeight: 1 }}>{info.blood_type}</div>
              </div>
            )}
          </div>
        </div>

        {/* Critical Alerts Section */}
        {(info.life_threatening_allergies.length > 0 || info.critical_conditions.length > 0) && (
          <div style={{ padding: '24px 32px', background: '#fff3cd', borderBottom: '2px solid #ffc107' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <svg viewBox="0 0 24 24" fill="none" style={{ width: '24px', height: '24px', flexShrink: 0 }}>
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke="#f57c00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#e65100', margin: 0, letterSpacing: '0.02em' }}>CRITICAL ALERTS</h3>
            </div>
            
            {info.life_threatening_allergies.length > 0 && (
              <div style={{ marginBottom: info.critical_conditions.length > 0 ? '16px' : '0' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#d32f2f', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>⚠️ Life-Threatening Allergies</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Array.from(new Set(info.life_threatening_allergies)).map((allergy, idx) => (
                    <div key={idx} style={{ background: '#ffebee', border: '2px solid #ef5350', borderRadius: '8px', padding: '8px 14px', fontSize: '14px', fontWeight: 700, color: '#b71c1c' }}>
                      {allergy}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {info.critical_conditions.length > 0 && (
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#f57c00', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🏥 Critical Conditions</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Array.from(new Set(info.critical_conditions)).map((condition, idx) => (
                    <div key={idx} style={{ background: 'white', border: '2px solid #ff9800', borderRadius: '8px', padding: '8px 14px', fontSize: '14px', fontWeight: 600, color: '#e65100' }}>
                      {condition}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Emergency Notes from AI */}
        {info.emergency_notes && (
          <div style={{ padding: '24px 32px', background: '#e3f2fd', borderBottom: '1px solid #90caf9' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ background: '#1976d2', borderRadius: '8px', padding: '8px', flexShrink: 0 }}>
                <svg viewBox="0 0 24 24" fill="none" style={{ width: '20px', height: '20px' }}>
                  <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#0d47a1', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🤖 AI Emergency Guidance</div>
                <p style={{ fontSize: '14px', color: '#1565c0', lineHeight: 1.6, margin: 0, fontWeight: 500 }}>{info.emergency_notes}</p>
              </div>
            </div>
          </div>
        )}

        {/* Emergency Contact */}
        {info.emergency_contact && (
          <div style={{ padding: '24px 32px', background: '#f3f4f6' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#374151', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📞 Emergency Contact</h3>
            <div style={{ background: 'white', border: '2px solid #e5e7eb', borderRadius: '12px', padding: '16px 20px' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#111827', marginBottom: '4px' }}>
                {info.emergency_contact.name || 'Contact on file'}
              </div>
              {info.emergency_contact.phone && (
                <a href={`tel:${info.emergency_contact.phone}`} style={{ fontSize: '18px', fontWeight: 800, color: '#1976d2', textDecoration: 'none', display: 'inline-block' }}>
                  {info.emergency_contact.phone}
                </a>
              )}
              {info.emergency_contact.relationship && (
                <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                  ({info.emergency_contact.relationship})
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ padding: '20px 32px', background: '#f9fafb', borderTop: '1px solid #e5e7eb', textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>
            Last Updated: {lastUpdated}
          </div>
          <div style={{ fontSize: '11px', color: '#d1d5db', marginTop: '4px' }}>
            This information is provided for emergency medical use only
          </div>
        </div>
      </div>

      {/* Bottom Notice */}
      <div style={{ maxWidth: '800px', margin: '24px auto 0', textAlign: 'center' }}>
        <div style={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(255,255,255,0.2)' }}>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>
            🔒 This page is publicly accessible for emergency purposes only
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', marginTop: '4px' }}>
            Information has been filtered by AI for emergency responder use
          </div>
        </div>
      </div>
    </div>
  );
}
