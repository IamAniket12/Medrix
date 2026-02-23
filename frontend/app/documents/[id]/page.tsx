'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';

interface DocumentDetail {
  document: {
    id: string;
    filename: string;
    file_path: string;
    file_size: number;
    mime_type: string;
    uploaded_at: string;
    document_type: string | null;
    document_date: string | null;
  };
  summary: {
    brief: string;
    clinical_overview: string;
    clinical_significance: string;
    urgency_level: string;
    key_findings: string[];
    treatment_plan: any;
    action_items: string[];
  } | null;
  clinical_data: {
    conditions: any[];
    medications: any[];
    allergies: any[];
    lab_results: any[];
    vital_signs: any[];
    procedures: any[];
    immunizations: any[];
  };
  timeline: any[];
}

export default function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  const [data, setData] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('summary');
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (documentId) {
      fetchDocumentDetails();
    }
  }, [documentId]);

  const fetchDocumentDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/v1/clinical/documents/demo_user_001/${documentId}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch document details');
      }

      const result = await response.json();
      setData(result);
      
      if (result.document.file_path) {
        const viewUrl = `http://localhost:8000/api/v1/files/view/${result.document.file_path}`;
        setFileUrl(viewUrl);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '60px',
            height: '60px',
            border: '3px solid rgba(249,115,22,0.2)',
            borderTop: '3px solid #f97316',
            borderRadius: '50%',
            margin: '0 auto 20px',
            animation: 'spin 1s linear infinite'
          }} />
          <p style={{
            color: '#78716c',
            fontSize: '16px',
            fontWeight: '500'
          }}>Loading document intelligence...</p>
        </div>
        <style dangerouslySetInnerHTML={{
          __html: `@keyframes spin { to { transform: rotate(360deg); } }`
        }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{
          background: '#ffffff',
          border: '1.5px solid rgba(0,0,0,0.06)',
          borderRadius: '24px',
          padding: '40px',
          maxWidth: '500px',
          textAlign: 'center',
          boxShadow: '0 4px 24px rgba(0,0,0,0.06)'
        }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>⚠️</div>
          <h2 style={{
            color: '#dc2626',
            fontSize: '24px',
            fontWeight: '800',
            marginBottom: '16px'
          }}>Error Loading Document</h2>
          <p style={{
            color: '#78716c',
            marginBottom: '32px',
            lineHeight: '1.6'
          }}>{error || 'Document not found'}</p>
          <button
            onClick={() => router.push('/documents')}
            style={{
              background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
              color: '#44403c',
              border: 'none',
              padding: '14px 32px',
              borderRadius: '12px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              width: '100%'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 12px 40px rgba(249,115,22,0.35)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            ← Back to Documents
          </button>
        </div>
      </div>
    );
  }

  const { document, summary, clinical_data } = data;
  const isImage = document.mime_type?.startsWith('image/');
  const isPDF = document.mime_type === 'application/pdf';

  const getUrgencyColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'critical': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#f59e0b';
      default: return '#10b981';
    }
  };

  const sections = [
    { key: 'summary', label: 'AI Summary', icon: '✨', count: summary ? 1 : 0 },
    { key: 'conditions', label: 'Conditions', icon: '🏥', count: clinical_data.conditions.length },
    { key: 'medications', label: 'Medications', icon: '💊', count: clinical_data.medications.length },
    { key: 'vitals', label: 'Vital Signs', icon: '❤️', count: clinical_data.vital_signs.length },
    { key: 'labs', label: 'Lab Results', icon: '🔬', count: clinical_data.lab_results.length },
    { key: 'procedures', label: 'Procedures', icon: '⚕️', count: clinical_data.procedures.length },
    { key: 'allergies', label: 'Allergies', icon: '⚠️', count: clinical_data.allergies.length },
  ];

  // Function to check if lab value is outside normal range
  const checkLabRange = (value: any, referenceRange: string | null): { isOutOfRange: boolean; status: 'HIGH' | 'LOW' | null } => {
    if (!referenceRange || !value) return { isOutOfRange: false, status: null };
    
    const numValue = parseFloat(String(value).replace(/[^\d.-]/g, ''));
    if (isNaN(numValue)) return { isOutOfRange: false, status: null };
    
    // Parse different range formats: "70-100", "< 5", "> 10", "≤ 5", "≥ 10"
    const rangeStr = referenceRange.trim();
    
    // Check for "less than" patterns
    const lessThanMatch = rangeStr.match(/^[<≤]\s*(\d+\.?\d*)/);
    if (lessThanMatch) {
      const maxValue = parseFloat(lessThanMatch[1]);
      if (numValue >= maxValue) return { isOutOfRange: true, status: 'HIGH' };
      return { isOutOfRange: false, status: null };
    }
    
    // Check for "greater than" patterns
    const greaterThanMatch = rangeStr.match(/^[>≥]\s*(\d+\.?\d*)/);
    if (greaterThanMatch) {
      const minValue = parseFloat(greaterThanMatch[1]);
      if (numValue <= minValue) return { isOutOfRange: true, status: 'LOW' };
      return { isOutOfRange: false, status: null };
    }
    
    // Check for range patterns: "70-100", "70 - 100", "70 to 100"
    const rangeMatch = rangeStr.match(/(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)/i);
    if (rangeMatch) {
      const minValue = parseFloat(rangeMatch[1]);
      const maxValue = parseFloat(rangeMatch[2]);
      
      if (numValue < minValue) return { isOutOfRange: true, status: 'LOW' };
      if (numValue > maxValue) return { isOutOfRange: true, status: 'HIGH' };
      return { isOutOfRange: false, status: null };
    }
    
    return { isOutOfRange: false, status: null };
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Animated Background Effects */}
      <div style={{
        position: 'fixed',
        top: '-50%',
        right: '-10%',
        width: '800px',
        height: '800px',
        background: 'radial-gradient(circle, rgba(249,115,22,0.12) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        pointerEvents: 'none',
        animation: 'float 20s ease-in-out infinite'
      }} />
      <div style={{
        position: 'fixed',
        bottom: '-30%',
        left: '-10%',
        width: '700px',
        height: '700px',
        background: 'radial-gradient(circle, rgba(251,113,133,0.1) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        pointerEvents: 'none',
        animation: 'float 25s ease-in-out infinite reverse'
      }} />

      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(30px, -30px) scale(1.1); }
          }
          @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
        `
      }} />

      <div style={{ maxWidth: '1600px', margin: '0 auto', position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{ marginBottom: '32px', animation: 'slideIn 0.6s ease-out' }}>
          <button
            onClick={() => router.push('/documents')}
            style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.08)',
              color: '#44403c',
              padding: '12px 24px',
              borderRadius: '12px',
              fontSize: '15px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '24px'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'rgba(249,115,22,0.06)';
              e.currentTarget.style.color = '#f97316';
              e.currentTarget.style.transform = 'translateX(-4px)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = '#ffffff';
              e.currentTarget.style.color = '#44403c';
              e.currentTarget.style.transform = 'translateX(0)';
            }}
          >
            ← Back to Documents
          </button>

          {/* Document Header Card */}
          <div style={{
            background: '#ffffff',
            border: '1.5px solid rgba(0,0,0,0.06)',
            borderRadius: '24px',
            padding: '32px',
            position: 'relative',
            overflow: 'hidden',
            boxShadow: '0 4px 24px rgba(0,0,0,0.06)'
          }}>
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '4px',
              background: 'linear-gradient(90deg, #f97316 0%, #fb7185 50%, #a78bfa 100%)',
            }} />
            
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '24px' }}>
              <div style={{ flex: 1, minWidth: '300px' }}>
                <div style={{
                  display: 'inline-block',
                  background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
                   color: '#44403c',
                  padding: '6px 14px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: '700',
                  letterSpacing: '0.5px',
                  marginBottom: '16px',
                  textTransform: 'uppercase'
                }}>
                  {document.document_type || 'Medical Record'}
                </div>
                
                <h1 style={{
                  fontSize: '36px',
                  fontWeight: '900',
                  color: '#1c1917',
                  marginBottom: '16px',
                  lineHeight: '1.2',
                  letterSpacing: '-0.02em'
                }}>
                  {document.filename}
                </h1>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', color: '#78716c', fontSize: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>📅</span>
                    <span>{formatDate(document.uploaded_at)}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>📦</span>
                    <span>{formatFileSize(document.file_size)}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>📄</span>
                    <span>{document.mime_type}</span>
                  </div>
                </div>
              </div>

              {/* Document Preview Button */}
              <button
                onClick={() => setShowPreview(!showPreview)}
                style={{
                  background: showPreview 
                    ? 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)'
                    : 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
                  color: 'white',
                  border: 'none',
                  padding: '16px 32px',
                  borderRadius: '16px',
                  fontSize: '16px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  boxShadow: showPreview 
                    ? '0 8px 32px rgba(139, 92, 246, 0.3)'
                    : '0 8px 32px rgba(249,115,22,0.3)',
                  minWidth: '200px',
                  justifyContent: 'center'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-3px)';
                  e.currentTarget.style.boxShadow = showPreview
                    ? '0 12px 40px rgba(139, 92, 246, 0.4)'
                    : '0 12px 40px rgba(249,115,22,0.4)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = showPreview
                    ? '0 8px 32px rgba(139, 92, 246, 0.3)'
                    : '0 8px 32px rgba(249,115,22,0.3)';
                }}
              >
                <span style={{ fontSize: '24px' }}>{showPreview ? '🙈' : '👁️'}</span>
                <span>{showPreview ? 'Hide Preview' : 'View Document'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Document Preview (Collapsible) */}
        {showPreview && (
          <div style={{
            marginBottom: '32px',
            animation: 'slideIn 0.6s ease-out'
          }}>
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              overflow: 'hidden',
              boxShadow: '0 4px 24px rgba(0,0,0,0.06)'
            }}>
              <h2 style={{
                fontSize: '24px',
                fontWeight: '800',
                color: '#1c1917',
                marginBottom: '24px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '28px' }}>📄</span>
                Document Preview
              </h2>

              {isImage && fileUrl && (
                <div style={{
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1.5px solid rgba(0,0,0,0.08)',
                  background: '#f9f9f7',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
                }}>
                  <img 
                    src={fileUrl} 
                    alt={document.filename} 
                    style={{ width: '100%', height: 'auto', display: 'block' }} 
                  />
                </div>
              )}
              
              {isPDF && fileUrl && (
                <div style={{
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1.5px solid rgba(0,0,0,0.08)',
                  background: 'white',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                  height: '800px'
                }}>
                  <iframe 
                    src={fileUrl} 
                    style={{ width: '100%', height: '100%', border: 'none' }} 
                    title={document.filename} 
                  />
                </div>
              )}
              
              {!fileUrl && (
                <div style={{
                  textAlign: 'center',
                  padding: '60px 20px',
                   color: '#78716c'
                }}>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                  <p style={{ fontSize: '16px', fontWeight: '600' }}>Loading preview...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation Pills */}
        <div style={{
          background: '#ffffff',
          border: '1.5px solid rgba(0,0,0,0.06)',
          borderRadius: '20px',
          padding: '16px',
          marginBottom: '32px',
          animation: 'slideIn 0.7s ease-out',
          overflowX: 'auto',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)'
        }}>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {sections.map((section) => (
              <button
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                style={{
                  background: activeSection === section.key
                    ? 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)'
                    : 'rgba(0,0,0,0.04)',
                  color: activeSection === section.key ? 'white' : '#44403c',
                  border: activeSection === section.key 
                    ? '1px solid transparent'
                    : '1px solid rgba(0,0,0,0.08)',
                  padding: '12px 20px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap',
                  boxShadow: activeSection === section.key
                    ? '0 4px 16px rgba(249,115,22,0.3)'
                    : 'none'
                }}
                onMouseOver={(e) => {
                  if (activeSection !== section.key) {
                    e.currentTarget.style.background = 'rgba(249,115,22,0.08)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }
                }}
                onMouseOut={(e) => {
                  if (activeSection !== section.key) {
                      e.currentTarget.style.background = 'rgba(0,0,0,0.04)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }
                }}
              >
                <span style={{ fontSize: '18px' }}>{section.icon}</span>
                <span>{section.label}</span>
                {section.count > 0 && (
                  <span style={{
                    background: activeSection === section.key 
                      ? 'rgba(255, 255, 255, 0.3)'
                      : 'rgba(249,115,22,0.15)',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '800'
                  }}>
                    {section.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Content Area */}
        <div style={{ animation: 'fadeIn 0.8s ease-out' }}>
          {/* AI Summary */}
          {activeSection === 'summary' && summary && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              marginBottom: '24px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
                <h2 style={{
                  fontSize: '28px',
                  fontWeight: '900',
                  color: '#1c1917',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <span style={{ fontSize: '32px' }}>✨</span>
                  AI-Generated Clinical Summary
                </h2>
                <div style={{
                  background: `linear-gradient(135deg, ${getUrgencyColor(summary.urgency_level)} 0%, ${getUrgencyColor(summary.urgency_level)}dd 100%)`,
                  color: 'white',
                  padding: '8px 16px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  fontWeight: '800',
                  letterSpacing: '0.5px',
                  textTransform: 'uppercase',
                  boxShadow: `0 4px 20px ${getUrgencyColor(summary.urgency_level)}40`
                }}>
                  {summary.urgency_level || 'routine'}
                </div>
              </div>

              <div style={{
                background: 'rgba(249,115,22,0.06)',
                border: '1px solid rgba(249,115,22,0.18)',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '32px',
                borderLeft: '4px solid #f97316'
              }}>
                <p style={{
                  color: '#1c1917',
                  fontSize: '18px',
                  lineHeight: '1.8',
                  margin: 0
                }}>
                  {summary.brief}
                </p>
              </div>

              {summary.key_findings && summary.key_findings.length > 0 && (
                <div style={{ marginBottom: '32px' }}>
                  <h3 style={{
                    fontSize: '20px',
                    fontWeight: '800',
                    color: '#1c1917',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}>
                    <span style={{ fontSize: '24px' }}>🔍</span>
                    Key Clinical Findings
                  </h3>
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {summary.key_findings.map((finding, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(139, 92, 246, 0.06)',
                          border: '1px solid rgba(139, 92, 246, 0.18)',
                          borderRadius: '12px',
                          padding: '16px 20px',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '12px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background = 'rgba(139, 92, 246, 0.06)';
                          e.currentTarget.style.transform = 'translateX(4px)';
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = 'rgba(139, 92, 246, 0.06)';
                          e.currentTarget.style.transform = 'translateX(0)';
                        }}
                      >
                        <span style={{
                          color: '#8b5cf6',
                          fontSize: '24px',
                          fontWeight: '900',
                          flexShrink: 0
                        }}>•</span>
                        <span style={{
                          color: '#1c1917',
                          fontSize: '16px',
                          lineHeight: '1.6',
                          flex: 1
                        }}>
                          {finding}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {summary.clinical_overview && (
                <div style={{
                  background: 'rgba(6, 182, 212, 0.06)',
                  border: '1px solid rgba(6, 182, 212, 0.18)',
                  borderRadius: '16px',
                  padding: '24px',
                  marginBottom: '24px'
                }}>
                  <h3 style={{
                    fontSize: '18px',
                    fontWeight: '800',
                        color: '#06b6d4',
                    marginBottom: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    Clinical Overview
                  </h3>
                  <p style={{
                    color: '#1c1917',
                    fontSize: '15px',
                    lineHeight: '1.7',
                    margin: 0
                  }}>
                    {summary.clinical_overview}
                  </p>
                </div>
              )}

              {summary.action_items && summary.action_items.length > 0 && (
                <div>
                  <h3 style={{
                    fontSize: '20px',
                    fontWeight: '800',
                    color: '#1c1917',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}>
                    <span style={{ fontSize: '24px' }}>📋</span>
                    Action Items
                  </h3>
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {summary.action_items.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(16, 185, 129, 0.06)',
                          border: '1px solid rgba(16, 185, 129, 0.18)',
                          borderRadius: '12px',
                          padding: '16px 20px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}
                      >
                        <input
                          type="checkbox"
                          style={{
                            width: '20px',
                            height: '20px',
                            cursor: 'pointer',
                            accentColor: '#10b981'
                          }}
                        />
                        <span style={{
                          color: '#1c1917',
                          fontSize: '16px',
                          flex: 1
                        }}>
                          {item}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Conditions */}
          {activeSection === 'conditions' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>🏥</span>
                Medical Conditions ({clinical_data.conditions.length})
              </h2>

              {clinical_data.conditions.length > 0 ? (
                <div style={{ display: 'grid', gap: '16px' }}>
                  {clinical_data.conditions.map((cond: any) => (
                    <div
                      key={cond.id}
                      style={{
                        background: 'rgba(249,115,22,0.04)',
                        border: '1px solid rgba(249,115,22,0.15)',
                        borderLeft: '4px solid #f97316',
                        borderRadius: '16px',
                        padding: '24px',
                        transition: 'all 0.3s ease'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 8px 32px rgba(249,115,22,0.15)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{
                        fontSize: '20px',
                        fontWeight: '700',
                         color: '#1c1917',
                        marginBottom: cond.status || cond.onset_date ? '16px' : 0
                      }}>
                        {cond.name}
                      </div>
                      
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                        {cond.status && (
                          <span style={{
                            background: 'rgba(249,115,22,0.12)',
                            color: '#f97316',
                            padding: '6px 14px',
                            borderRadius: '8px',
                            fontSize: '13px',
                            fontWeight: '700',
                            textTransform: 'capitalize'
                          }}>
                            {cond.status}
                          </span>
                        )}
                        {cond.onset_date && (
                          <span style={{
                            color: '#78716c',
                            fontSize: '14px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}>
                            <span>📅</span>
                            Since: {new Date(cond.onset_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>🏥</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No conditions extracted</p>
                </div>
              )}
            </div>
          )}

          {/* Medications */}
          {activeSection === 'medications' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>💊</span>
                Medications ({clinical_data.medications.length})
              </h2>

              {clinical_data.medications.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                  {clinical_data.medications.map((med: any) => (
                    <div
                      key={med.id}                      style={{
                        background: 'rgba(16,185,129,0.05)',
                        border: '1px solid rgba(16,185,129,0.18)',
                        borderLeft: '4px solid #10b981',
                        borderRadius: '16px',
                        padding: '24px',
                        transition: 'all 0.3s ease'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 8px 32px rgba(16,185,129,0.2)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{
                        fontSize: '20px',
                        fontWeight: '700',
                         color: '#1c1917',
                        marginBottom: '12px'
                      }}>
                        {med.name}
                      </div>
                      
                      {(med.dosage || med.frequency || med.route) && (
              <div style={{ color: '#78716c', fontSize: '15px', marginBottom: '12px', lineHeight: '1.6' }}>
                          {med.dosage && <div>💊 {med.dosage}</div>}
                          {med.route && <div>📍 {med.route}</div>}
                        </div>
                      )}

                      {med.status && (
                        <span style={{
                          background: 'rgba(16,185,129,0.12)',
                          color: '#34d399',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: '700',
                          textTransform: 'capitalize',
                          display: 'inline-block'
                        }}>
                          {med.status}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>💊</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No medications extracted</p>
                </div>
              )}
            </div>
          )}

          {/* Vital Signs */}
          {activeSection === 'vitals' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>❤️</span>
                Vital Signs
              </h2>

              {clinical_data.vital_signs.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '20px' }}>
                  {clinical_data.vital_signs.map((vital: any) => {
                    const vitalsToDisplay = [];
                    
                    if (vital.systolic_bp && vital.diastolic_bp) {
                      vitalsToDisplay.push({
                        type: 'Blood Pressure',
                        value: `${vital.systolic_bp}/${vital.diastolic_bp}`,
                        unit: 'mmHg',
                        icon: '🩸'
                      });
                    }
                    
                    if (vital.heart_rate) vitalsToDisplay.push({ type: 'Heart Rate', value: vital.heart_rate, unit: 'bpm', icon: '❤️' });
                    if (vital.temperature) vitalsToDisplay.push({ type: 'Temperature', value: vital.temperature, unit: vital.temperature_unit || '°F', icon: '🌡️' });
                    if (vital.respiratory_rate) vitalsToDisplay.push({ type: 'Respiratory Rate', value: vital.respiratory_rate, unit: '/min', icon: '🫁' });
                    if (vital.oxygen_saturation) vitalsToDisplay.push({ type: 'O₂ Saturation', value: vital.oxygen_saturation, unit: '%', icon: '💨' });
                    if (vital.weight) vitalsToDisplay.push({ type: 'Weight', value: vital.weight, unit: vital.weight_unit || 'kg', icon: '⚖️' });
                    if (vital.height) vitalsToDisplay.push({ type: 'Height', value: vital.height, unit: vital.height_unit || 'cm', icon: '📏' });
                    if (vital.bmi) vitalsToDisplay.push({ type: 'BMI', value: vital.bmi, unit: 'kg/m²', icon: '📊' });
                    
                    return vitalsToDisplay.map((v, idx) => (
                      <div
                        key={`${vital.id}-${idx}`}
                        style={{
                          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          borderLeft: '4px solid #ef4444',
                          borderRadius: '16px',
                          padding: '24px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.transform = 'translateY(-4px)';
                          e.currentTarget.style.boxShadow = '0 8px 32px rgba(239, 68, 68, 0.3)';
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      >
                        <div style={{
                          fontSize: '11px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          color: '#78716c',
                          marginBottom: '8px',
                          fontWeight: '700'
                        }}>
                          {v.icon} {v.type}
                        </div>
                        <div style={{
                          fontSize: '36px',
                          fontWeight: '900',
                          color: '#1c1917',
                          marginBottom: '4px'
                        }}>
                          {v.value}
                        </div>
                        <div style={{
                          fontSize: '14px',
                          color: '#78716c',
                          fontWeight: '600'
                        }}>
                          {v.unit}
                        </div>
                        {vital.measurement_date && (
                          <div style={{
                            marginTop: '12px',
                            paddingTop: '12px',
                             borderTop: '1px solid rgba(0,0,0,0.06)',
                            fontSize: '12px',
                             color: '#a8a29e'
                          }}>
                            📅 {new Date(vital.measurement_date).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    ));
                  })}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>❤️</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No vital signs extracted</p>
                </div>
              )}
            </div>
          )}

          {/* Lab Results */}
          {activeSection === 'labs' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>🔬</span>
                Laboratory Results ({clinical_data.lab_results.length})
              </h2>

              {clinical_data.lab_results.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                  {clinical_data.lab_results.map((lab: any) => {
                    const rangeCheck = checkLabRange(lab.value, lab.reference_range);
                    const isAbnormal = lab.is_abnormal || rangeCheck.isOutOfRange;
                    
                    return (
                      <div
                        key={lab.id}
                        style={{
                          background: isAbnormal
                            ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%)'
                            : 'rgba(139,92,246,0.04)',
                          border: isAbnormal 
                            ? '1px solid rgba(239, 68, 68, 0.3)'
                            : '1px solid rgba(139,92,246,0.15)',
                          borderLeft: isAbnormal 
                            ? '4px solid #ef4444'
                            : '4px solid #8b5cf6',
                          borderRadius: '16px',
                          padding: '24px',
                          transition: 'all 0.3s ease',
                          position: 'relative'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.transform = 'translateY(-4px)';
                          e.currentTarget.style.boxShadow = isAbnormal
                            ? '0 8px 32px rgba(239, 68, 68, 0.3)'
                            : '0 8px 32px rgba(139,92,246,0.15)';
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      >
                        {isAbnormal && (
                          <div style={{
                            position: 'absolute',
                            top: '16px',
                            right: '16px',
                            background: '#ef4444',
                             color: 'white',
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: '900',
                            fontSize: '16px',
                            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)'
                          }}>
                            !
                          </div>
                        )}
                        
                        <div style={{
                          fontSize: '14px',
                          fontWeight: '700',
                           color: '#78716c',
                          marginBottom: '12px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px'
                        }}>
                          {lab.test_name}
                        </div>
                        
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
                          <div style={{
                            fontSize: '40px',
                            fontWeight: '900',
                             color: '#44403c'
                          }}>
                            {lab.value}
                          </div>
                          
                          {rangeCheck.status && (
                            <div style={{
                              background: rangeCheck.status === 'HIGH' 
                                ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                                : 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                               color: 'white',
                              padding: '4px 10px',
                              borderRadius: '8px',
                              fontSize: '12px',
                              fontWeight: '800',
                              letterSpacing: '0.5px',
                              boxShadow: rangeCheck.status === 'HIGH'
                                ? '0 4px 12px rgba(239, 68, 68, 0.4)'
                                : '0 4px 12px rgba(249, 115, 22, 0.4)',
                              animation: 'pulse 2s ease-in-out infinite'
                            }}>
                              {rangeCheck.status === 'HIGH' ? '↑ HIGH' : '↓ LOW'}
                            </div>
                          )}
                        </div>
                        
                        <div style={{
                          fontSize: '16px',
                           color: '#78716c',
                          fontWeight: '600',
                          marginBottom: '16px'
                        }}>
                          {lab.unit}
                        </div>

                        {(lab.reference_range || lab.test_date) && (
                          <div style={{
                            paddingTop: '16px',
                             borderTop: '1px solid rgba(0,0,0,0.06)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            fontSize: '13px',
                             color: '#a8a29e'
                          }}>
                            {lab.reference_range && (
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                 color: rangeCheck.isOutOfRange ? '#fca5a5' : '#a8a29e',
                                fontWeight: rangeCheck.isOutOfRange ? '700' : '400'
                              }}>
                                📊 Normal: {lab.reference_range}
                              </div>
                            )}
                            {lab.test_date && <div>📅 {new Date(lab.test_date).toLocaleDateString()}</div>}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>🔬</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No lab results extracted</p>
                </div>
              )}
            </div>
          )}

          {/* Procedures */}
          {activeSection === 'procedures' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>⚕️</span>
                Medical Procedures ({clinical_data.procedures.length})
              </h2>

              {clinical_data.procedures.length > 0 ? (
                <div style={{ display: 'grid', gap: '16px' }}>
                  {clinical_data.procedures.map((proc: any) => (
                    <div
                      key={proc.id}
                      style={{
                        background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.1) 0%, rgba(249, 115, 22, 0.05) 100%)',
                        border: '1px solid rgba(249, 115, 22, 0.2)',
                        borderLeft: '4px solid #f97316',
                        borderRadius: '16px',
                        padding: '24px',
                        transition: 'all 0.3s ease'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 8px 32px rgba(249, 115, 22, 0.3)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{
                        fontSize: '20px',
                        fontWeight: '700',
                         color: '#1c1917',
                        marginBottom: '12px'
                      }}>
                        {proc.procedure_name}
                      </div>
                      
                      {proc.outcome && (
                        <div style={{
                           color: '#78716c',
                          fontSize: '15px',
                          lineHeight: '1.6',
                          marginBottom: '12px'
                        }}>
                          {proc.outcome}
                        </div>
                      )}

                      {proc.procedure_date && (
                        <div style={{
                           color: '#a8a29e',
                          fontSize: '14px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <span>📅</span>
                          {new Date(proc.procedure_date).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>⚕️</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No procedures extracted</p>
                </div>
              )}
            </div>
          )}

          {/* Allergies */}
          {activeSection === 'allergies' && (
            <div style={{
              background: '#ffffff',
              border: '1.5px solid rgba(0,0,0,0.06)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.05)'
            }}>
              <h2 style={{
                fontSize: '28px',
                fontWeight: '900',
                color: '#1c1917',
                marginBottom: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <span style={{ fontSize: '32px' }}>⚠️</span>
                Allergies & Adverse Reactions ({clinical_data.allergies.length})
              </h2>

              {clinical_data.allergies.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                  {clinical_data.allergies.map((allergy: any) => (
                    <div
                      key={allergy.id}
                      style={{
                        background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.1) 0%, rgba(234, 179, 8, 0.05) 100%)',
                        border: '1px solid rgba(234, 179, 8, 0.3)',
                        borderLeft: '4px solid #eab308',
                        borderRadius: '16px',
                        padding: '24px',
                        transition: 'all 0.3s ease'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 8px 32px rgba(234, 179, 8, 0.3)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{
                        fontSize: '20px',
                        fontWeight: '700',
                         color: '#1c1917',
                        marginBottom: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        ⚠️ {allergy.allergen}
                      </div>
                      
                      {allergy.reaction && (
                        <div style={{
                           color: '#78716c',
                          fontSize: '15px',
                          lineHeight: '1.6',
                          marginBottom: '12px'
                        }}>
                           <strong style={{ color: '#78716c' }}>Reaction:</strong> {allergy.reaction}
                        </div>
                      )}

                      {allergy.severity && (
                        <span style={{
                          background: allergy.severity.toLowerCase() === 'severe' 
                            ? 'rgba(239, 68, 68, 0.2)'
                            : 'rgba(234, 179, 8, 0.2)',
                          color: allergy.severity.toLowerCase() === 'severe' ? '#991b1b' : '#854d0e',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          display: 'inline-block'
                        }}>
                          {allergy.severity}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#a8a29e' }}>
                  <div style={{ fontSize: '64px', marginBottom: '16px' }}>⚠️</div>
                  <p style={{ fontSize: '16px', fontWeight: '600', color: '#78716c' }}>No allergies recorded</p>
                  <p style={{ fontSize: '14px', marginTop: '8px' }}>This is good news! 🎉</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
