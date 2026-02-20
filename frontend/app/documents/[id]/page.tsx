'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

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
  const [activeSection, setActiveSection] = useState<string>('all');

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
        const urlResponse = await fetch(
          `http://localhost:8000/api/v1/files/view/${result.document.file_path}`
        );
        if (urlResponse.ok) {
          const urlData = await urlResponse.json();
          setFileUrl(urlData.url);
        }
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
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">⚠️ Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">{error || 'Document not found'}</p>
            <Button onClick={() => router.push('/documents')} className="mt-4 w-full">
              Back to Documents
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { document, summary, clinical_data } = data;
  const isImage = document.mime_type?.startsWith('image/');
  const isPDF = document.mime_type === 'application/pdf';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="outline"
            onClick={() => router.push('/documents')}
            className="mb-4 bg-white hover:bg-gray-50 shadow-sm"
          >
            ← Back to Documents
          </Button>
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {document.filename}
            </h1>
            <p className="text-gray-600 mt-2 flex items-center gap-2">
              <span>📅</span>
              Uploaded on {formatDate(document.uploaded_at)}
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: Document Preview (3 columns) */}
          <div className="lg:col-span-3 space-y-6">
            {/* Document Viewer */}
            <Card className="shadow-lg border-none overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
                <CardTitle className="flex items-center gap-2">
                  <span>📄</span>
                  Document Preview
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 bg-gray-50">
                {isImage && fileUrl && (
                  <div className="rounded-lg overflow-hidden border-2 border-gray-200 bg-white shadow-inner">
                    <img src={fileUrl} alt={document.filename} className="w-full h-auto" />
                  </div>
                )}
                {isPDF && fileUrl && (
                  <div className="rounded-lg border-2 border-gray-200 bg-white">
                    <iframe src={fileUrl} className="w-full h-[700px]" title={document.filename} />
                  </div>
                )}
                {!fileUrl && (isImage || isPDF) && (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading preview...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* AI Summary */}
            {summary && (
              <Card className="shadow-lg border-none overflow-hidden">
                <CardHeader className="bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <span>✨</span>
                      AI-Generated Summary
                    </CardTitle>
                    <Badge className="bg-white/20 text-white border-white/30 backdrop-blur-sm">
                      {(summary.urgency_level || 'routine').replace(/-/g, ' ').toUpperCase()}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <p className="text-gray-700 leading-relaxed text-lg">{summary.brief}</p>
                  
                  {summary.key_findings && summary.key_findings.length > 0 && (
                    <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-5 border-l-4 border-purple-500">
                      <h4 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                        <span>🔍</span>
                        Key Clinical Findings
                      </h4>
                      <ul className="space-y-2">
                        {summary.key_findings.map((finding, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-gray-700">
                            <span className="text-purple-500 font-bold text-lg">•</span>
                            <span className="flex-1">{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right: Clinical Data (2 columns) */}
          <div className="lg:col-span-2">
            <Card className="shadow-lg border-none overflow-hidden sticky top-4">
              <CardHeader className="bg-gradient-to-r from-teal-600 via-cyan-600 to-blue-600 text-white">
                <CardTitle className="flex items-center gap-2">
                  <span className="text-2xl">🤖</span>
                  Clinical Data Extraction
                </CardTitle>
                <CardDescription className="text-teal-50">
                  AI-powered multi-agent medical information extraction
                </CardDescription>
              </CardHeader>
              
              <CardContent className="p-0">
                {/* Modern Filter Pills */}
                <div className="p-4 bg-gradient-to-r from-gray-50 to-blue-50 border-b">
                  <div className="flex flex-wrap gap-2">
                    {[
                      { key: 'all', label: 'All', color: 'teal', count: null },
                      { key: 'conditions', label: 'Conditions', color: 'blue', count: clinical_data.conditions.length },
                      { key: 'medications', label: 'Meds', color: 'green', count: clinical_data.medications.length },
                      { 
                        key: 'vitals', 
                        label: 'Vitals', 
                        color: 'red', 
                        count: clinical_data.vital_signs.reduce((sum: number, v: any) => {
                          let count = 0;
                          if (v.systolic_bp && v.diastolic_bp) count++;
                          if (v.heart_rate) count++;
                          if (v.temperature) count++;
                          if (v.respiratory_rate) count++;
                          if (v.oxygen_saturation) count++;
                          if (v.weight) count++;
                          if (v.height) count++;
                          if (v.bmi) count++;
                          return sum + count;
                        }, 0)
                      },
                      { key: 'labs', label: 'Labs', color: 'purple', count: clinical_data.lab_results.length },
                      { key: 'procedures', label: 'Procedures', color: 'orange', count: clinical_data.procedures.length },
                      { key: 'allergies', label: 'Allergies', color: 'yellow', count: clinical_data.allergies.length },
                    ].map(({ key, label, color, count }) => (
                      <button
                        key={key}
                        onClick={() => setActiveSection(key)}
                        className={`px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200 ${
                          activeSection === key
                            ? `bg-${color}-600 text-white shadow-lg scale-105`
                            : 'bg-white text-gray-700 hover:bg-gray-100 shadow-sm'
                        }`}
                      >
                        {label} {count !== null && `(${count})`}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Content Area with Smooth Animations */}
                <div className="p-5 max-h-[750px] overflow-y-auto bg-white">
                  {/* All View */}
                  {activeSection === 'all' && (
                    <div className="space-y-5 animate-fadeIn">
                      {/* Conditions */}
                      {clinical_data.conditions.length > 0 && (
                        <section>
                          <h3 className="font-bold text-blue-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">🏥</span>
                            Conditions ({clinical_data.conditions.length})
                          </h3>
                          <div className="space-y-2">
                            {clinical_data.conditions.map((cond: any) => (
                              <div key={cond.id} className="bg-gradient-to-r from-blue-50 to-blue-100/50 border-l-4 border-blue-500 p-4 rounded-r-lg hover:shadow-md transition-all">
                                <div className="font-semibold text-gray-900">{cond.name}</div>
                                {cond.status && (
                                  <Badge className="mt-2 bg-blue-100 text-blue-800 border-blue-200">{cond.status}</Badge>
                                )}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Medications */}
                      {clinical_data.medications.length > 0 && (
                        <section>
                          <h3 className="font-bold text-green-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">💊</span>
                            Medications ({clinical_data.medications.length})
                          </h3>
                          <div className="space-y-2">
                            {clinical_data.medications.map((med: any) => (
                              <div key={med.id} className="bg-gradient-to-r from-green-50 to-green-100/50 border-l-4 border-green-500 p-4 rounded-r-lg hover:shadow-md transition-all">
                                <div className="font-semibold text-gray-900">{med.name}</div>
                                {(med.dosage || med.frequency) && (
                                  <div className="text-sm text-gray-600 mt-1">
                                    {med.dosage} {med.frequency && `• ${med.frequency}`}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Vital Signs */}
                      {clinical_data.vital_signs.length > 0 && (
                        <section>
                          <h3 className="font-bold text-red-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">❤️</span>
                            Vital Signs
                          </h3>
                          <div className="grid grid-cols-2 gap-3">
                            {clinical_data.vital_signs.map((vital: any) => {
                              // Transform flattened DB format to displayable vitals
                              const vitalsToDisplay = [];
                              
                              if (vital.systolic_bp && vital.diastolic_bp) {
                                vitalsToDisplay.push({
                                  type: 'Blood Pressure',
                                  value: `${vital.systolic_bp}/${vital.diastolic_bp}`,
                                  unit: 'mmHg'
                                });
                              }
                              
                              if (vital.heart_rate) {
                                vitalsToDisplay.push({
                                  type: 'Heart Rate',
                                  value: vital.heart_rate,
                                  unit: 'bpm'
                                });
                              }
                              
                              if (vital.temperature) {
                                vitalsToDisplay.push({
                                  type: 'Temperature',
                                  value: vital.temperature,
                                  unit: vital.temperature_unit || '°F'
                                });
                              }
                              
                              if (vital.respiratory_rate) {
                                vitalsToDisplay.push({
                                  type: 'Respiratory Rate',
                                  value: vital.respiratory_rate,
                                  unit: '/min'
                                });
                              }
                              
                              if (vital.oxygen_saturation) {
                                vitalsToDisplay.push({
                                  type: 'O₂ Saturation',
                                  value: vital.oxygen_saturation,
                                  unit: '%'
                                });
                              }
                              
                              if (vital.weight) {
                                vitalsToDisplay.push({
                                  type: 'Weight',
                                  value: vital.weight,
                                  unit: vital.weight_unit || 'kg'
                                });
                              }
                              
                              if (vital.height) {
                                vitalsToDisplay.push({
                                  type: 'Height',
                                  value: vital.height,
                                  unit: vital.height_unit || 'cm'
                                });
                              }
                              
                              if (vital.bmi) {
                                vitalsToDisplay.push({
                                  type: 'BMI',
                                  value: vital.bmi,
                                  unit: 'kg/m²'
                                });
                              }
                              
                              return vitalsToDisplay.map((v, idx) => (
                                <div key={`${vital.id}-${idx}`} className="bg-gradient-to-br from-red-50 to-red-100/50 border-l-4 border-red-500 p-3 rounded-r-lg hover:shadow-md transition-all">
                                  <div className="text-xs text-gray-600 uppercase tracking-wide">{v.type}</div>
                                  <div className="text-2xl font-bold text-gray-900 mt-1">{v.value}</div>
                                  <div className="text-xs text-gray-500 mt-1">{v.unit}</div>
                                  {vital.measurement_date && (
                                    <div className="text-xs text-gray-400 mt-1">
                                      {new Date(vital.measurement_date).toLocaleDateString()}
                                    </div>
                                  )}
                                </div>
                              ));
                            })}
                          </div>
                        </section>
                      )}

                      {/* Labs (Top 5) */}
                      {clinical_data.lab_results.length > 0 && (
                        <section>
                          <h3 className="font-bold text-purple-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">🔬</span>
                            Lab Results ({clinical_data.lab_results.length})
                          </h3>
                          <div className="space-y-2">
                            {clinical_data.lab_results.slice(0, 5).map((lab: any) => (
                              <div key={lab.id} className={`border-l-4 p-4 rounded-r-lg hover:shadow-md transition-all ${
                                lab.is_abnormal ? 'bg-gradient-to-r from-red-50 to-red-100/50 border-red-500' : 'bg-gradient-to-r from-purple-50 to-purple-100/50 border-purple-500'
                              }`}>
                                <div className="flex justify-between items-start mb-2">
                                  <div className="font-semibold text-gray-900 text-sm">{lab.test_name}</div>
                                  {lab.is_abnormal && <Badge className="bg-red-600 text-white">!</Badge>}
                                </div>
                                <div className="text-2xl font-bold text-gray-900">
                                  {lab.value} <span className="text-base text-gray-600">{lab.unit}</span>
                                </div>
                              </div>
                            ))}
                            {clinical_data.lab_results.length > 5 && (
                              <p className="text-center text-sm text-gray-500 italic pt-2">
                                +{clinical_data.lab_results.length - 5} more • Click "Labs" to view all
                              </p>
                            )}
                          </div>
                        </section>
                      )}

                      {/* Procedures */}
                      {clinical_data.procedures.length > 0 && (
                        <section>
                          <h3 className="font-bold text-orange-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">⚕️</span>
                            Procedures ({clinical_data.procedures.length})
                          </h3>
                          <div className="space-y-2">
                            {clinical_data.procedures.map((proc: any) => (
                              <div key={proc.id} className="bg-gradient-to-r from-orange-50 to-orange-100/50 border-l-4 border-orange-500 p-4 rounded-r-lg hover:shadow-md transition-all">
                                <div className="font-semibold text-gray-900">{proc.procedure_name}</div>
                                {proc.outcome && (
                                  <div className="text-sm text-gray-600 mt-1">{proc.outcome}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Allergies */}
                      {clinical_data.allergies.length > 0 && (
                        <section>
                          <h3 className="font-bold text-yellow-700 mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <span className="text-lg">⚠️</span>
                            Allergies ({clinical_data.allergies.length})
                          </h3>
                          <div className="space-y-2">
                            {clinical_data.allergies.map((allergy: any) => (
                              <div key={allergy.id} className="bg-gradient-to-r from-yellow-50 to-yellow-100/50 border-l-4 border-yellow-500 p-4 rounded-r-lg hover:shadow-md transition-all">
                                <div className="font-semibold text-gray-900">{allergy.allergen}</div>
                                {allergy.reaction && (
                                  <div className="text-sm text-gray-600 mt-1">{allergy.reaction}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Empty State */}
                      {clinical_data.conditions.length === 0 && 
                       clinical_data.medications.length === 0 && 
                       clinical_data.vital_signs.length === 0 && 
                       clinical_data.lab_results.length === 0 && 
                       clinical_data.procedures.length === 0 && 
                       clinical_data.allergies.length === 0 && (
                        <div className="text-center py-16">
                          <span className="text-6xl mb-4 block">🤷</span>
                          <p className="text-lg font-semibold text-gray-600">No Clinical Data Extracted</p>
                          <p className="text-sm text-gray-500 mt-2">The AI couldn't extract medical information from this document</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Individual Section Views */}
                  {activeSection !== 'all' && (
                    <div className="animate-fadeIn">
                      {/* You can add detailed individual views for each section here */}
                      <p className="text-gray-500 text-center py-8">
                        Detailed view for {activeSection} coming soon...
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
