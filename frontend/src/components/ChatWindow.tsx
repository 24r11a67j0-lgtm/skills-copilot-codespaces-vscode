'use client';

import { useEffect, useRef } from 'react';
import { Bot, User } from 'lucide-react';
import VideoCard from './VideoCard';
import clsx from 'clsx';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

// Parse [VIDEO: title | url | thumbnail] markers from assistant replies
function parseMessageContent(content: string): React.ReactNode[] {
  const videoRegex = /\[VIDEO:\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^\]]*)\]/g;
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = videoRegex.exec(content)) !== null) {
    const [fullMatch, title, url, thumbnail] = match;
    const before = content.slice(lastIndex, match.index);
    if (before) nodes.push(<span key={lastIndex}>{before}</span>);
    nodes.push(
      <VideoCard
        key={match.index}
        title={title.trim()}
        url={url.trim()}
        thumbnail={thumbnail.trim()}
      />,
    );
    lastIndex = match.index + fullMatch.length;
  }

  const remaining = content.slice(lastIndex);
  if (remaining) nodes.push(<span key={lastIndex}>{remaining}</span>);
  return nodes;
}

interface Props {
  messages: Message[];
  isLoading: boolean;
}

export default function ChatWindow({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
          <Bot className="w-12 h-12 text-brand-300" />
          <p className="text-sm text-center">
            Paste a YouTube channel URL above, then ask me anything about the content!
          </p>
        </div>
      )}

      {messages.map((msg, i) => (
        <div
          key={i}
          className={clsx('flex gap-3 max-w-3xl', {
            'ml-auto flex-row-reverse': msg.role === 'user',
          })}
        >
          {/* Avatar */}
          <div
            className={clsx(
              'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold',
              msg.role === 'assistant' ? 'bg-brand-600' : 'bg-slate-600',
            )}
          >
            {msg.role === 'assistant' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
          </div>

          {/* Bubble */}
          <div
            className={clsx(
              'rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap',
              msg.role === 'assistant'
                ? 'bg-white border border-slate-200 text-slate-800'
                : 'bg-brand-600 text-white',
            )}
          >
            {msg.role === 'assistant'
              ? parseMessageContent(msg.content)
              : msg.content}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex gap-3 max-w-3xl">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white">
            <Bot className="w-4 h-4" />
          </div>
          <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 flex items-center gap-1">
            <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
