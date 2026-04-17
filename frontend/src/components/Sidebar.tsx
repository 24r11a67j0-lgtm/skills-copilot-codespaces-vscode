'use client';

import { BookOpen, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import VideoCard from './VideoCard';
import type { TopicsResponse, LearningStep } from '@/lib/api';
import { getLearningPath } from '@/lib/api';

interface Props {
  channelId: string;
  topics: TopicsResponse['topics'];
  onTopicSelect: (topic: string) => void;
}

export default function Sidebar({ channelId, topics, onTopicSelect }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [paths, setPaths] = useState<Record<string, LearningStep[]>>({});
  const [loading, setLoading] = useState<string | null>(null);

  const handleTopicClick = async (topicName: string) => {
    if (expanded === topicName) {
      setExpanded(null);
      return;
    }
    setExpanded(topicName);
    onTopicSelect(topicName);

    if (!paths[topicName]) {
      setLoading(topicName);
      try {
        const res = await getLearningPath(channelId, topicName);
        setPaths((prev) => ({ ...prev, [topicName]: res.data.steps }));
      } catch {
        // ignore
      } finally {
        setLoading(null);
      }
    }
  };

  return (
    <aside className="w-72 min-h-screen border-r border-slate-200 bg-white flex flex-col">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center gap-2 text-brand-600 font-bold text-lg">
          <BookOpen className="w-5 h-5" />
          Topics
        </div>
        <p className="text-xs text-slate-500 mt-1">{topics.length} topics found</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {topics.map((topic) => (
          <div key={topic.name} className="border-b border-slate-100">
            <button
              onClick={() => handleTopicClick(topic.name)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">{topic.name}</p>
                <p className="text-xs text-slate-500">{topic.videos?.length ?? 0} videos</p>
              </div>
              {expanded === topic.name ? (
                <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
              )}
            </button>

            {expanded === topic.name && (
              <div className="px-3 pb-3 space-y-2">
                {loading === topic.name ? (
                  <p className="text-xs text-slate-400 text-center py-2 animate-pulse">
                    Building learning path…
                  </p>
                ) : paths[topic.name]?.length ? (
                  paths[topic.name].map((step) => (
                    <VideoCard
                      key={step.video_id}
                      title={step.video_title}
                      url={step.video_url}
                      thumbnail={step.thumbnail}
                      reason={step.reason}
                      order={step.order}
                    />
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-2">
                    No learning path generated yet.
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
