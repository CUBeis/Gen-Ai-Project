/**
 * Backend API client for the demo UI.
 * In dev, use empty VITE_API_BASE_URL so requests go through Vite proxy → :8000.
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export function getApiBaseUrl(): string {
  return API_BASE_URL || window.location.origin;
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const url = API_BASE_URL ? `${API_BASE_URL}/health` : '/health';
    const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(4000) });
    if (!response.ok) return false;
    const data = (await response.json()) as { status?: string };
    return data.status === 'ok';
  } catch {
    return false;
  }
}

interface DemoChatResponse {
  response_text: string;
  intent_detected: string;
  language: string;
  sources?: Array<Record<string, unknown>>;
}

export async function sendDemoChatMessage(
  sessionId: string,
  message: string
): Promise<DemoChatResponse> {
  const url = `${API_BASE_URL}/api/v1/chat/demo`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        image_base64: null,
      }),
      signal: AbortSignal.timeout(120000),
    });
  } catch (error) {
    const hint = getApiBaseUrl();
    throw new Error(
      `Cannot reach the backend at ${hint}. Start it with: cd Backend && uvicorn main:app --reload --port 8000`
    );
  }

  if (!response.ok) {
    const details = await response.text();
    throw new Error(details || `Chat request failed with HTTP ${response.status}`);
  }

  return response.json() as Promise<DemoChatResponse>;
}
