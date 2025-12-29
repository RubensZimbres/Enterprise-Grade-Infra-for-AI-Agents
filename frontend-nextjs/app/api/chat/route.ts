import { NextRequest, NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const auth = new GoogleAuth();

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Use server-side only env var (not NEXT_PUBLIC_)
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8080';

    if (!backendUrl) {
      console.error('BACKEND_URL environment variable is not configured');
      return NextResponse.json(
        { error: 'Backend URL not configured.' },
        { status: 500 }
      );
    }

    // Validate request body
    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json(
        { error: 'Invalid request: message is required' },
        { status: 400 }
      );
    }

    // Extract User Identity Token (Firebase) from Client Request
    const userAuthToken = req.headers.get('Authorization');
    if (!userAuthToken) {
        return NextResponse.json(
            { error: 'Unauthorized: Missing User Token' },
            { status: 401 }
        );
    }
    // Remove "Bearer " prefix if present to be clean, but usually headers forward it as is. 
    // We will forward it in X-Firebase-Token, which expects the raw token in our backend logic? 
    // Backend logic: `decoded_token = auth.verify_id_token(x_firebase_token)`
    // verify_id_token expects just the token string.
    const firebaseToken = userAuthToken.replace('Bearer ', '');

    console.log(`Forwarding request to: ${backendUrl}/stream`);

    // Get Service-to-Service OIDC auth headers (Identity of the Frontend Service)
    let serviceAuthHeaders = {};
    if (!backendUrl.includes('localhost')) {
      try {
        // For Cloud Run, the audience is the URL of the receiving service
        const client = await auth.getIdTokenClient(backendUrl);
        serviceAuthHeaders = await client.getRequestHeaders();
        console.log('Generated Service-to-Service OIDC token');
      } catch (err) {
        console.error('Failed to get service-to-service ID token:', err);
      }
    }

    // Forward the request to the internal backend
    const response = await fetch(`${backendUrl}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        
        // 1. Service Identity (Who is calling? The Frontend Service)
        // Uses standard Authorization: Bearer <OIDC_TOKEN>
        ...serviceAuthHeaders,

        // 2. User Identity (Who is the user? The Firebase User)
        // Passed in a custom header to avoid conflict with Service Identity
        'X-Firebase-Token': firebaseToken,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      console.error(`Backend error: ${response.status} - ${errorText}`);
      if (response.status === 401) {
           return NextResponse.json({ error: 'Unauthorized Backend Access' }, { status: 401 });
      }
      return NextResponse.json(
        { error: `Backend error: ${errorText}` },
        { status: response.status }
      );
    }

    if (!response.body) {
      return NextResponse.json(
        { error: 'Empty response from backend' },
        { status: 502 }
      );
    }

    // Proxy the stream back to the client
    return new Response(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    });

  } catch (error) {
    console.error('Proxy error:', error);

    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Unable to connect to backend service' },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS preflight
export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
