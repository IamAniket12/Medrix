'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface DocumentSummary {
  id: string;
  filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  uploaded_at: string;
  document_type: string | null;
  document_date: string | null;
  extraction_status: string;
  summary: {
    brief: string | null;
    urgency_level: string;
  };
  counts: {
    conditions: number;
    medications: number;
    labs: number;
  };
}

const urgencyColors = {
  critical: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.25)', text: '#dc2626' },
  urgent: { bg: 'rgba(234,88,12,0.1)', border: 'rgba(234,88,12,0.25)', text: '#ea580c' },
  'follow-up-needed': { bg: 'rgba(202,138,4,0.1)', border: 'rgba(202,138,4,0.25)', text: '#ca8a04' },
  routine: { bg: 'rgba(22,163,74,0.1)', border: 'rgba(22,163,74,0.25)', text: '#16a34a' },
};

const docTypeIcons: Record<string, string> = {
  lab_report: '🧪',
  prescription: '💊',
  discharge_summary: '🏥',
  consultation: '👨‍⚕️',
  imaging: '📸',
  unknown: '📄',
};

const docTypeLabels: Record<string, string> = {
  lab_report: 'Lab Report',
  prescription: 'Prescription',
  discharge_summary: 'Discharge Summary',
  consultation: 'Consultation',
  imaging: 'Imaging Report',
  unknown: 'Medical Document',
};

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [user, setUser] = useState<{ id: string; name: string; email: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem('medrix_user');
    const parsed = raw ? JSON.parse(raw) : null;
    setUser(parsed);
    setAuthChecked(true);
    if (parsed) fetchDocuments(parsed.id);
    else setLoading(false);
  }, []);

  const fetchDocuments = async (userId?: string) => {
    try {
      setLoading(true);
      const id = userId || user?.id;
      const response = await fetch(`http://localhost:8000/api/v1/clinical/documents/${id}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      setDocuments(data.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const filteredDocuments = filterType === 'all' 
    ? documents 
    : documents.filter(doc => doc.document_type === filterType);

  const documentTypes = ['all', ...Array.from(new Set(documents.map(d => d.document_type).filter((t): t is string => t !== null)))];

  if (!authChecked || (loading && !user)) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(249,115,22,0.2)', borderTop: '3px solid #f97316', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <div style={{ maxWidth: '440px', width: '100%', background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '24px', padding: '48px 40px', textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.07)' }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>🔒</div>
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#1c1917', marginBottom: '10px' }}>Sign in to view your documents</h2>
          <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '32px', lineHeight: 1.6 }}>Your medical records are private. Please sign in to access them.</p>
          <button onClick={() => router.push('/signin')} style={{ padding: '13px 32px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 16px rgba(249,115,22,0.3)', width: '100%' }}>
            Sign In
          </button>
          <p style={{ marginTop: '16px', fontSize: '13px', color: '#a8a29e' }}>Don&apos;t have an account? <button onClick={() => router.push('/signin')} style={{ background: 'none', border: 'none', color: '#f97316', fontWeight: 700, cursor: 'pointer', fontSize: '13px', padding: 0 }}>Create one</button></p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: '56px', height: '56px', border: '4px solid rgba(249,115,22,0.15)', borderTop: '4px solid #f97316', borderRadius: '50%', margin: '0 auto 24px', animation: 'spin 1s linear infinite' }} />
          <div style={{ fontSize: '18px', fontWeight: 600, color: '#78716c' }}>Loading documents...</div>
        </div>
        <style jsx>{`
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <div style={{ maxWidth: '500px', width: '100%', background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '20px', padding: '40px', textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
          <div style={{ fontSize: '64px', marginBottom: '24px' }}>⚠️</div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#1c1917', marginBottom: '12px' }}>Error Loading Documents</h2>
          <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '28px' }}>{error}</p>
          <button onClick={() => fetchDocuments()} style={{ padding: '12px 28px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 4px 16px rgba(249,115,22,0.3)' }}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', position: 'relative' }}>
      <div style={{ position: 'absolute', top: '10%', right: '10%', width: '400px', height: '400px', background: 'radial-gradient(circle, rgba(249,115,22,0.1) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(60px)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '20%', left: '5%', width: '350px', height: '350px', background: 'radial-gradient(circle, rgba(251,113,133,0.08) 0%, transparent 70%)', borderRadius: '50%', filter: 'blur(50px)', pointerEvents: 'none' }} />
      
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px 24px', position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{ marginBottom: '48px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h1 style={{ fontSize: '48px', fontWeight: 800, color: '#1c1917', marginBottom: '8px', letterSpacing: '-0.01em' }}>Medical Documents</h1>
              <p style={{ fontSize: '16px', color: '#78716c' }}>
                {filteredDocuments.length} {filteredDocuments.length === 1 ? 'document' : 'documents'} in your health record
              </p>
            </div>
            <button 
              onClick={() => router.push('/upload')}
              style={{ padding: '14px 24px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 8px 24px rgba(249,115,22,0.3)' }}
            >
              <span style={{ fontSize: '18px' }}>📤</span>
              Upload Document
            </button>
          </div>
          
          {/* Filters */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '24px' }}>
            {documentTypes.map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                style={{
                  padding: '8px 16px',
                  background: filterType === type ? 'rgba(249,115,22,0.1)' : '#ffffff',
                  border: filterType === type ? '1.5px solid rgba(249,115,22,0.35)' : '1.5px solid rgba(0,0,0,0.08)',
                  borderRadius: '10px',
                  color: filterType === type ? '#f97316' : '#78716c',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: filterType === type ? 'none' : '0 1px 4px rgba(0,0,0,0.04)',
                }}
              >
                {type === 'all' ? 'All Documents' : docTypeLabels[type] || type}
              </button>
            ))}
          </div>
        </div>

        {/* Documents Grid */}
        {filteredDocuments.length === 0 ? (
          <div style={{ background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '24px', padding: '80px 40px', textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: '80px', marginBottom: '24px' }}>📄</div>
            <h3 style={{ fontSize: '24px', fontWeight: 700, color: '#1c1917', marginBottom: '12px' }}>No documents {filterType !== 'all' ? 'of this type' : 'yet'}</h3>
            <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '32px' }}>
              {filterType !== 'all' ? 'Try a different filter' : 'Upload your first medical document to get started'}
            </p>
            {filterType === 'all' && (
              <button 
                onClick={() => router.push('/upload')}
                style={{ padding: '14px 28px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 4px 16px rgba(249,115,22,0.3)' }}
              >
                Upload Document
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '24px' }}>
            {filteredDocuments.map((doc) => {
              const urgency = doc.summary?.urgency_level as keyof typeof urgencyColors;
              const urgencyStyle = urgencyColors[urgency] || urgencyColors.routine;
              const docIcon = docTypeIcons[doc.document_type || 'unknown'] || '📄';
              
              return (
                <div
                  key={doc.id}
                  onClick={() => router.push(`/documents/${doc.id}`)}
                  style={{
                    background: '#ffffff',
                    border: '1.5px solid rgba(0,0,0,0.06)',
                    borderRadius: '20px',
                    padding: '24px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    position: 'relative',
                    overflow: 'hidden',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-6px)';
                    e.currentTarget.style.borderColor = 'rgba(249,115,22,0.3)';
                    e.currentTarget.style.boxShadow = '0 16px 40px rgba(249,115,22,0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)';
                    e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.04)';
                  }}
                >
                  <div style={{ position: 'absolute', top: 0, right: 0, width: '150px', height: '150px', background: 'radial-gradient(circle, rgba(249,115,22,0.06), transparent)', borderRadius: '50%', filter: 'blur(20px)', pointerEvents: 'none' }} />
                  
                  <div style={{ position: 'relative', zIndex: 1 }}>
                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                          <span style={{ fontSize: '28px' }}>{docIcon}</span>
                          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#1c1917', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {doc.filename}
                          </h3>
                        </div>
                        <div style={{ fontSize: '13px', color: '#a8a29e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>📅</span>
                          {formatDate(doc.uploaded_at)}
                        </div>
                      </div>
                      <div style={{ fontSize: '20px', color: '#f97316', opacity: 0.7 }}>→</div>
                    </div>

                    {/* Tags */}
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                      {doc.document_type && (
                        <span style={{ padding: '4px 10px', background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#f97316' }}>
                          {docTypeLabels[doc.document_type] || doc.document_type}
                        </span>
                      )}
                      {urgency && (
                        <span style={{ padding: '4px 10px', background: urgencyStyle.bg, border: `1px solid ${urgencyStyle.border}`, borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: urgencyStyle.text }}>
                          {doc.summary.urgency_level.replace(/-/g, ' ')}
                        </span>
                      )}
                    </div>

                    {/* Summary */}
                    {doc.summary.brief && (
                      <p style={{ fontSize: '14px', color: '#78716c', lineHeight: 1.6, marginBottom: '20px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {doc.summary.brief}
                      </p>
                    )}

                    {/* Clinical Data Counts */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', padding: '16px 0', borderTop: '1px solid rgba(0,0,0,0.06)', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: '#f97316', marginBottom: '4px' }}>{doc.counts.conditions}</div>
                        <div style={{ fontSize: '11px', color: '#a8a29e', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Conditions</div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: '#16a34a', marginBottom: '4px' }}>{doc.counts.medications}</div>
                        <div style={{ fontSize: '11px', color: '#a8a29e', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Medications</div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: '#a78bfa', marginBottom: '4px' }}>{doc.counts.labs}</div>
                        <div style={{ fontSize: '11px', color: '#a8a29e', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Lab Tests</div>
                      </div>
                    </div>

                    {/* Footer metadata */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', fontSize: '12px', color: '#a8a29e' }}>
                      <span>{formatFileSize(doc.file_size)}</span>
                      {doc.document_date && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span>🕐</span>
                          {formatDate(doc.document_date)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
