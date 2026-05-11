/**
 * Central API client for Sovereignty AI Studio.
 * Connects all frontend pages to backend services via the node-bridge.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:9899/api/v1';
const BRIDGE_BASE_URL = API_BASE_URL.replace(/\/api\/v1$/, '');

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => response.statusText);
    throw new Error(`API Error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

// ── Health & Status ────────────────────────────────────────────────────
export const HealthAPI = {
  check: () => request<{ status: string }>('/status'),
  bridgeHealth: () =>
    fetch(`${BRIDGE_BASE_URL}/health`).then((r) => r.json()),
  bridgeStatus: () =>
    fetch(`${BRIDGE_BASE_URL}/api/bridge/status`).then((r) => r.json()),
};

// ── Voice ──────────────────────────────────────────────────────────────
export const VoiceAPI = {
  chat: (text: string, voice_model?: string) =>
    request<{
      input: string;
      response: string;
      audio_file: string | null;
      status: string;
    }>('/voice/chat', {
      method: 'POST',
      body: JSON.stringify({ text, voice_model }),
    }),

  speak: (text: string) =>
    request<{ status: string; message: string; audio_file: string | null }>(
      '/voice/speak',
      { method: 'POST', body: JSON.stringify({ text }) }
    ),

  status: () => request<{ piper_tts: object; voice_models: string[]; status: string }>('/voice/status'),
};

// ── Avatar ─────────────────────────────────────────────────────────────
export const AvatarAPI = {
  getState: () => request<Record<string, unknown>>('/avatar/state'),

  interact: (message: string) =>
    request<{ response: string; mood: string; expression: string }>(
      '/avatar/interact',
      { method: 'POST', body: JSON.stringify({ message }) }
    ),

  updateMood: (mood: string) =>
    request<Record<string, unknown>>('/avatar/mood', {
      method: 'PUT',
      body: JSON.stringify({ mood }),
    }),

  toggleEEGLink: (enabled: boolean) =>
    request<Record<string, unknown>>('/avatar/eeg-link', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
};

// ── Media Generator ────────────────────────────────────────────────────
export const MediaAPI = {
  generate: (user_id: string, media_type: string, prompt: string) =>
    request<Record<string, unknown>>('/studio/media/generate', {
      method: 'POST',
      body: JSON.stringify({ user_id, media_type, prompt }),
    }),

  getJob: (jobId: string) =>
    request<Record<string, unknown>>(`/studio/media/job/${jobId}`),

  list: (file_type?: string) =>
    request<Array<Record<string, unknown>>>(`/media${file_type ? `?file_type=${file_type}` : ''}`),
};

// ── Music ──────────────────────────────────────────────────────────────
export const MusicAPI = {
  compose: (prompt: string, genre: string, duration_seconds: number, bpm?: number) =>
    request<Record<string, unknown>>('/music/compose', {
      method: 'POST',
      body: JSON.stringify({ prompt, genre, duration_seconds, bpm }),
    }),

  list: () => request<Array<Record<string, unknown>>>('/music'),

  genres: () => request<{ genres: Array<Record<string, unknown>> }>('/music/genres'),
};

// ── Generation (Story, etc.) ───────────────────────────────────────────
export const GenerationAPI = {
  create: (generation_type: string, prompt: string, parameters?: Record<string, unknown>, project_id?: number) =>
    request<{ id: number; status: string; generation_type: string; message: string }>(
      '/generation/',
      {
        method: 'POST',
        body: JSON.stringify({ generation_type, prompt, parameters, project_id }),
      }
    ),

  list: (generation_type?: string) =>
    request<Array<Record<string, unknown>>>(
      `/generation${generation_type ? `?generation_type=${generation_type}` : ''}`
    ),

  get: (id: number) => request<Record<string, unknown>>(`/generation/${id}`),

  supportedTypes: () => request<{ types: Record<string, unknown> }>('/generation/types/supported'),
};

// ── Dashboard / Project Builder ────────────────────────────────────────
export const ProjectAPI = {
  create: (user_id: string, name: string, project_type: string) =>
    request<Record<string, unknown>>('/studio/dashboard/project', {
      method: 'POST',
      body: JSON.stringify({ user_id, name, project_type }),
    }),

  build: (projectId: string) =>
    request<Record<string, unknown>>(`/studio/dashboard/build/${projectId}`, {
      method: 'POST',
    }),

  status: () => request<Record<string, unknown>>('/studio/dashboard/status'),
};

// ── Syntax Checker ─────────────────────────────────────────────────────
export const SyntaxAPI = {
  check: (code: string, filename?: string) =>
    request<Record<string, unknown>>('/syntax/check', {
      method: 'POST',
      body: JSON.stringify({ code, filename }),
    }),

  colors: () => request<{ colors: Record<string, unknown> }>('/syntax/colors'),
};
