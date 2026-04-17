'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, RefreshCcw } from 'lucide-react';

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
  onNewSession: () => void;
  placeholder?: string;
}

export default function ChatInput({ onSend, disabled, onNewSession, placeholder }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <button
          onClick={onNewSession}
          title="New conversation"
          className="flex-shrink-0 p-2 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
        >
          <RefreshCcw className="w-4 h-4" />
        </button>

        <div className="flex-1 border border-slate-300 rounded-2xl overflow-hidden focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100 transition-all bg-white">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={placeholder || 'Ask anything about the channel…'}
            className="w-full px-4 py-3 text-sm resize-none outline-none disabled:bg-slate-50 text-slate-800 placeholder-slate-400"
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className="flex-shrink-0 p-3 rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {disabled ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
      <p className="text-xs text-center text-slate-400 mt-2">
        Press Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
