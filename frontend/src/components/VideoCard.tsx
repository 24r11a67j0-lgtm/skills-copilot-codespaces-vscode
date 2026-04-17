'use client';

import Image from 'next/image';
import { ExternalLink } from 'lucide-react';

interface Props {
  title: string;
  url: string;
  thumbnail: string;
  reason?: string;
  order?: number;
}

function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
      return url;
    }
  } catch {
    // fall through
  }
  return '#';
}

export default function VideoCard({ title, url, thumbnail, reason, order }: Props) {
  return (
    <a
      href={sanitizeUrl(url)}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 p-3 rounded-xl border border-slate-200 bg-white hover:border-brand-500 hover:shadow-md transition-all group"
    >
      {/* Thumbnail */}
      <div className="relative flex-shrink-0 w-28 h-16 rounded-lg overflow-hidden bg-slate-100">
        {thumbnail ? (
          <Image src={thumbnail} alt={title} fill sizes="112px" className="object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400 text-xs">
            No image
          </div>
        )}
        {order !== undefined && (
          <span className="absolute top-1 left-1 bg-brand-600 text-white text-xs font-bold w-5 h-5 flex items-center justify-center rounded-full">
            {order}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 line-clamp-2 group-hover:text-brand-600">
          {title}
        </p>
        {reason && (
          <p className="text-xs text-slate-500 mt-1 line-clamp-2">{reason}</p>
        )}
        <span className="inline-flex items-center gap-1 text-xs text-brand-500 mt-1">
          Watch <ExternalLink className="w-3 h-3" />
        </span>
      </div>
    </a>
  );
}
