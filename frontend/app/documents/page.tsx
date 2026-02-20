'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

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
  critical: 'bg-red-100 text-red-800 border-red-200',
  urgent: 'bg-orange-100 text-orange-800 border-orange-200',
  'follow-up-needed': 'bg-yellow-100 text-yellow-800 border-yellow-200',
  routine: 'bg-green-100 text-green-800 border-green-200',
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

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/v1/clinical/documents/demo_user_001');
      
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your documents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              ⚠️ Error Loading Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">{error}</p>
            <Button onClick={fetchDocuments} className="mt-4 w-full">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Medical Documents</h1>
          <p className="mt-2 text-gray-600">
            {documents.length} {documents.length === 1 ? 'document' : 'documents'} in your health record
          </p>
        </div>

        {/* Documents Grid */}
        {documents.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <div className="text-6xl mb-4">📄</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No documents yet</h3>
              <p className="text-gray-600 mb-4">Upload your first medical document to get started</p>
              <Button onClick={() => router.push('/upload')}>
                Upload Document
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {documents.map((doc) => (
              <Card
                key={doc.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
                onClick={() => router.push(`/documents/${doc.id}`)}
              >
                <CardHeader className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-lg truncate group-hover:text-blue-600 transition-colors">
                        {doc.filename}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        📅 {formatDate(doc.uploaded_at)}
                      </CardDescription>
                    </div>
                    <span className="text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all">
                      →
                    </span>
                  </div>

                  {/* Document Type & Urgency */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {doc.document_type && (
                      <Badge variant="outline" className="font-normal">
                        {docTypeLabels[doc.document_type] || doc.document_type}
                      </Badge>
                    )}
                    {doc.summary?.urgency_level && (
                      <Badge
                        variant="outline"
                        className={`font-normal ${urgencyColors[doc.summary.urgency_level as keyof typeof urgencyColors] || urgencyColors.routine}`}
                      >
                        {doc.summary.urgency_level.replace(/-/g, ' ')}
                      </Badge>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Summary */}
                  {doc.summary.brief && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {doc.summary.brief}
                    </p>
                  )}

                  {/* Clinical Data Counts */}
                  <div className="grid grid-cols-3 gap-2 pt-3 border-t">
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-blue-600 mb-1">
                        <span className="text-lg font-semibold">{doc.counts.conditions}</span>
                      </div>
                      <p className="text-xs text-gray-500">Conditions</p>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-green-600 mb-1">
                        <span className="text-lg font-semibold">{doc.counts.medications}</span>
                      </div>
                      <p className="text-xs text-gray-500">Medications</p>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-purple-600 mb-1">
                        <span className="text-lg font-semibold">{doc.counts.labs}</span>
                      </div>
                      <p className="text-xs text-gray-500">Lab Tests</p>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t">
                    <span>{formatFileSize(doc.file_size)}</span>
                    {doc.document_date && (
                      <span>🕐 {formatDate(doc.document_date)}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
