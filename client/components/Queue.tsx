"use client";

import QueuedCall from "./generic/QueuedCall";
import QueuedCallSkeleton from "./generic/QueuedCallSkeleton";
import { QueueItem } from "@/lib/api";

export type SimilaritySuppressedNotice = {
  id: string;
  duplicate_of?: string | null;
  notice?: string | null;
  createdAt: number;
};

interface QueueProps {
  data: QueueItem[] | undefined;
  isPending: boolean;
  error: Error | null;
  onSelectCall: (id: string) => void;
  selectedCallId: string | null;
  suppressedNotices?: SimilaritySuppressedNotice[];
  onDismissSuppressed?: (id: string) => void;
}

export default function Queue({
  data,
  isPending,
  error,
  onSelectCall,
  selectedCallId,
  suppressedNotices,
  onDismissSuppressed
}: QueueProps) {
  if (isPending && !data) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <QueuedCallSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) return <div className="text-red-400">An error has occurred: {error.message}</div>;

  const hasSuppressed = (suppressedNotices?.length ?? 0) > 0;
  if ((!data || data.length === 0) && !hasSuppressed) {
    return <div className="text-zinc-400">No calls in queue.</div>;
  }

  return (
    <div className="space-y-2">
      {hasSuppressed && (
        <div className="space-y-2">
          {suppressedNotices!.map((n) => (
            <div
              key={n.id}
              className="rounded-md border border-amber-600/40 bg-amber-900/20 p-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-amber-200 text-sm font-semibold">
                    Similarity hit (not added to queue)
                  </div>
                  <div className="text-amber-100/80 text-xs mt-1 break-words">
                    {n.notice ?? "A similar incident was detected and suppressed."}
                  </div>
                  <div className="text-amber-100/70 text-xs mt-1">
                    New: …{n.id.slice(-8)}
                    {n.duplicate_of ? ` • Similar to: …${n.duplicate_of.slice(-8)}` : null}
                  </div>
                </div>
                {onDismissSuppressed && (
                  <button
                    className="text-amber-200/80 hover:text-amber-100 text-xs whitespace-nowrap"
                    onClick={() => onDismissSuppressed(n.id)}
                  >
                    Dismiss
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {data?.map((call) => (
        <QueuedCall
          key={call.id}
          id={call.id}
          type={call.incidentType}
          location={call.location}
          time={call.time}
          severity={Number(call.severity_level) || 1}
          suggestedAction={call.suggested_actions}
          callers={1}
          onSelectCall={onSelectCall}
          isSelected={call.id === selectedCallId}
        />
      ))}
    </div>
  );
}
