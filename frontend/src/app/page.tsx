'use client';

import { useState, useCallback, useRef } from 'react';
import { Youtube, Loader2, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import ChatWindow, { Message } from '@/components/ChatWindow';
import ChatInput from '@/components/ChatInput';
import Sidebar from '@/components/Sidebar';
import {
  analyseChannel,
  getStatus,
  getTopics,
  sendChat,
  clearSession,
  TopicsResponse,
  StatusResponse,
} from '@/lib/api';

type IndexStatus = 'idle' | 'loading' | 'ready' | 'error';

export default function Home() {
  const [channelUrl, setChannelUrl] = useState('');
  const [channelId, setChannelId] = useState('');
  const [channelTitle, setChannelTitle] = useState('');
  const [indexStatus, setIndexStatus] = useState<IndexStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [topics, setTopics] = useState<TopicsResponse['topics']>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const sessionIdRef = useRef<string>('');
  const pollInterval = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  };

  const pollStatus = useCallback(
    (cid: string) => {
      pollInterval.current = setInterval(async () => {
        try {
          const res = await getStatus(cid);
          const data: StatusResponse = res.data;

          if (data.status === 'ready') {
            stopPolling();
            setChannelTitle(data.channel_title || cid);
            setStatusMessage(
              `✓ Indexed ${data.video_count ?? '?'} videos from "${data.channel_title}"`,
            );
            setIndexStatus('ready');

            // Load topics
            const topicRes = await getTopics(cid);
            setTopics(topicRes.data.topics);

            // Welcome message
            setMessages([
              {
                role: 'assistant',
                content: `👋 I've analysed **${data.channel_title}**!\n\nI found **${data.video_count}** videos and **${topicRes.data.topics.length}** topic areas. Check the sidebar to explore topics, or just ask me anything!\n\nFor example:\n• "What topics does this channel cover?"\n• "I want to learn [topic] — where should I start?"\n• "Show me the best beginner videos"`,
              },
            ]);
          } else if (data.status === 'error') {
            stopPolling();
            setIndexStatus('error');
            setStatusMessage(`Error: ${data.error}`);
          } else {
            setStatusMessage(
              data.status === 'fetching'
                ? 'Fetching videos from YouTube…'
                : 'Indexing and embedding content…',
            );
          }
        } catch {
          // Keep polling
        }
      }, 3000);
    },
    [],
  );

  const handleAnalyse = async () => {
    if (!channelUrl.trim()) return;
    setIndexStatus('loading');
    setStatusMessage('Starting analysis…');
    setMessages([]);
    setTopics([]);
    stopPolling();

    try {
      const res = await analyseChannel(channelUrl.trim());
      const { channel_id, job } = res.data;
      setChannelId(channel_id);

      if (job.status === 'ready') {
        setChannelTitle(job.channel_title || channel_id);
        setStatusMessage(`✓ Already indexed "${job.channel_title}"`);
        setIndexStatus('ready');
        const topicRes = await getTopics(channel_id);
        setTopics(topicRes.data.topics);
        setMessages([
          {
            role: 'assistant',
            content: `👋 Welcome back! I already have data on **${job.channel_title}**.\n\nAsk me anything about the content, or explore topics in the sidebar.`,
          },
        ]);
      } else {
        pollStatus(channel_id);
      }
    } catch (err: unknown) {
      setIndexStatus('error');
      const message =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Unknown error'
          : 'Unknown error';
      setStatusMessage(`Error: ${message}`);
    }
  };

  const handleReindex = async () => {
    if (!channelUrl.trim()) return;
    setIndexStatus('loading');
    setStatusMessage('Re-indexing channel…');
    setMessages([]);
    setTopics([]);
    stopPolling();

    try {
      const res = await analyseChannel(channelUrl.trim(), true);
      pollStatus(res.data.channel_id);
      setChannelId(res.data.channel_id);
    } catch {
      setIndexStatus('error');
      setStatusMessage('Re-index failed.');
    }
  };

  const handleSend = async (message: string) => {
    if (!channelId) return;
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setChatLoading(true);

    try {
      const res = await sendChat(channelId, message, sessionIdRef.current, channelTitle);
      sessionIdRef.current = res.data.session_id;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠️ Something went wrong. Please try again.' },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleNewSession = async () => {
    if (sessionIdRef.current) {
      await clearSession(sessionIdRef.current).catch(() => {});
      sessionIdRef.current = '';
    }
    setMessages(
      indexStatus === 'ready'
        ? [{ role: 'assistant', content: '🔄 New conversation started! Ask me anything.' }]
        : [],
    );
  };

  const handleTopicSelect = (topic: string) => {
    if (indexStatus !== 'ready') return;
    handleSend(`I want to learn about "${topic}". Give me a structured learning path with the best videos to watch in order.`);
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar — only show when ready */}
      {indexStatus === 'ready' && topics.length > 0 && (
        <Sidebar
          channelId={channelId}
          topics={topics}
          onTopicSelect={handleTopicSelect}
        />
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center">
              <Youtube className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-slate-800 text-lg leading-none">
                Content Learning Guide
              </h1>
              <p className="text-xs text-slate-500">AI-powered learning path generator</p>
            </div>
          </div>

          {/* URL input */}
          <div className="flex gap-2">
            <input
              type="url"
              value={channelUrl}
              onChange={(e) => setChannelUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyse()}
              placeholder="https://www.youtube.com/@channelname"
              disabled={indexStatus === 'loading'}
              className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-100 disabled:text-slate-400"
            />
            <button
              onClick={handleAnalyse}
              disabled={indexStatus === 'loading' || !channelUrl.trim()}
              className="px-5 py-2 bg-brand-600 text-white text-sm font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {indexStatus === 'loading' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Analyse'
              )}
            </button>
            {indexStatus === 'ready' && (
              <button
                onClick={handleReindex}
                title="Re-index channel"
                className="p-2 border border-slate-300 rounded-xl text-slate-500 hover:text-brand-600 hover:border-brand-400 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Status bar */}
          {statusMessage && (
            <div
              className={`mt-2 flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg ${
                indexStatus === 'error'
                  ? 'bg-red-50 text-red-600'
                  : indexStatus === 'ready'
                  ? 'bg-green-50 text-green-700'
                  : 'bg-brand-50 text-brand-600'
              }`}
            >
              {indexStatus === 'error' ? (
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              ) : indexStatus === 'ready' ? (
                <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
              ) : (
                <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
              )}
              {statusMessage}
            </div>
          )}
        </header>

        {/* Chat area */}
        <ChatWindow messages={messages} isLoading={chatLoading} />

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={chatLoading || indexStatus !== 'ready'}
          onNewSession={handleNewSession}
          placeholder={
            indexStatus === 'ready'
              ? 'Ask about topics, learning paths, or specific videos…'
              : 'Analyse a channel first to start chatting…'
          }
        />
      </div>
    </div>
  );
}
