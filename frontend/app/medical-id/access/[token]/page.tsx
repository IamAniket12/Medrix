'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const API_BASE_URL = 'http://localhost:8000/api/v1';

interface AccessResult {
  success: boolean;
  signed_url?: string;
  error?: string;
}

export default function AccessPage() {
  const params = useParams();
  const accessToken = params.token as string;
  
  const [loading, setLoading] = useState(true);
  const [accessResult, setAccessResult] = useState<AccessResult | null>(null);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    verifyAccess();
  }, [accessToken]);

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const verifyAccess = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/medical-id/access/${accessToken}`
      );
      const data: AccessResult = await response.json();
      setAccessResult(data);
      
      if (data.success && data.signed_url) {
        // Auto-redirect to PDF after 3 seconds
        setCountdown(3);
        setTimeout(() => {
          window.location.href = data.signed_url!;
        }, 3000);
      }
    } catch (err) {
      setAccessResult({
        success: false,
        error: 'Failed to connect to server',
      });
    } finally {
      setLoading(false);
    }
  };

  const openPDF = () => {
    if (accessResult?.signed_url) {
      window.open(accessResult.signed_url, '_blank');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Verifying access...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!accessResult?.success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <div className="text-center mb-4">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <svg
                  className="w-8 h-8 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </div>
            </div>
            <CardTitle className="text-center">Access Denied</CardTitle>
            <CardDescription className="text-center">
              This medical summary is no longer accessible
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-800">
                {accessResult?.error || 'Invalid or expired access token'}
              </p>
            </div>
            
            <div className="text-sm text-gray-600 space-y-2">
              <p className="font-semibold">Possible reasons:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>The 5-minute access window has expired</li>
                <li>The maximum view limit (5 times) has been reached</li>
                <li>The patient has revoked access</li>
                <li>The access link is invalid</li>
              </ul>
            </div>

            <div className="mt-6">
              <p className="text-sm text-gray-600 text-center">
                Please request a new access link from the patient.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="text-center mb-4">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <svg
                className="w-8 h-8 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          </div>
          <CardTitle className="text-center">Access Granted</CardTitle>
          <CardDescription className="text-center">
            Medical summary is ready to view
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Badge variant="outline" className="bg-white">
                ✓ Authorized Access
              </Badge>
            </div>
            <p className="text-sm text-green-800 text-center">
              You have been granted temporary access to view this medical summary
            </p>
          </div>

          {countdown > 0 && (
            <div className="text-center mb-4">
              <p className="text-sm text-gray-600">
                Redirecting to PDF in {countdown} seconds...
              </p>
            </div>
          )}

          <Button onClick={openPDF} className="w-full mb-4">
            View Medical Summary
          </Button>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <svg
                className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="text-sm text-blue-800">
                <p className="font-semibold mb-1">Important Notice:</p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>This medical information is confidential</li>
                  <li>For authorized healthcare providers only</li>
                  <li>Access expires after 5 minutes or 5 views</li>
                  <li>Do not share this link with others</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              Powered by Medrix Medical ID System
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
