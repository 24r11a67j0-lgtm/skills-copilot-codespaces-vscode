import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_URL });

export interface AnalyseResponse {
  channel_id: string;
  job: { status: string; progress: number; channel_title?: string; video_count?: number };
}

export interface StatusResponse {
  channel_id: string;
  status: string;
  progress: number;
  channel_title?: string;
  video_count?: number;
  error?: string;
}

export interface TopicsResponse {
  topics: Array<{
    name: string;
    description: string;
    video_ids: string[];
    videos: VideoMeta[];
  }>;
}

export interface VideoMeta {
  video_id: string;
  video_title: string;
  video_url: string;
  thumbnail: string;
  published_at: string;
  view_count: number;
}

export interface LearningStep {
  order: number;
  video_id: string;
  video_title: string;
  video_url: string;
  thumbnail: string;
  reason: string;
}

export interface LearningPathResponse {
  topic: string;
  steps: LearningStep[];
}

export interface ChatResponse {
  session_id: string;
  reply: string;
}

export interface SearchResult {
  video_id: string;
  video_title: string;
  video_url: string;
  thumbnail: string;
  score: number;
}

export const analyseChannel = (channelUrl: string, forceReindex = false) =>
  api.post<AnalyseResponse>('/analyse', { channel_url: channelUrl, force_reindex: forceReindex });

export const getStatus = (channelId: string) =>
  api.get<StatusResponse>(`/status/${channelId}`);

export const getTopics = (channelId: string) =>
  api.get<TopicsResponse>(`/topics/${channelId}`);

export const getLearningPath = (channelId: string, topic: string) =>
  api.post<LearningPathResponse>('/learning-path', { channel_id: channelId, topic });

export const searchVideos = (channelId: string, query: string, nResults = 8) =>
  api.post<{ results: SearchResult[] }>('/search', {
    channel_id: channelId,
    query,
    n_results: nResults,
  });

export const sendChat = (
  channelId: string,
  message: string,
  sessionId: string,
  channelTitle: string,
) =>
  api.post<ChatResponse>('/chat', {
    channel_id: channelId,
    message,
    session_id: sessionId,
    channel_title: channelTitle,
  });

export const clearSession = (sessionId: string) =>
  api.delete(`/session/${sessionId}`);
