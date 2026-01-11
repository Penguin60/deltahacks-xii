"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Queue from "@/components/Queue";
import DispatcherStatus from "@/components/DispatcherStatus";
import Sidebar, { LogEntry } from "@/components/Sidebar";
import { mockTranscripts, TranscriptIn } from "@/lib/mock-data";
import {
	useDispatchers,
	SimulationConfig,
	CustomCall,
} from "@/hooks/useDispatchers";
import {
	fetchQueue,
	invokeTranscript,
	removeFromQueue,
	type TimestampedTranscriptLine,
	type InvokeResponse,
} from "@/lib/api";
import Link from "next/link";

const DEFAULT_CONFIG: SimulationConfig = {
	dispatchers: 5,
	incomingCalls: 10,
	handleTime: "3",
	initialBusyDispatchers: 0,
	initialBusyHandleTime: "1",
	customIncomingCalls: [],
	customCurrentCalls: [],
};

function parseDurationToSeconds(duration: string): number | null {
	// Expected formats in this repo: "MM:SS" (e.g. "03:52") or occasionally "HH:MM:SS"
	const parts = duration.split(":").map((p) => Number(p));
	if (parts.some((n) => Number.isNaN(n))) return null;
	if (parts.length === 2) {
		const [mm, ss] = parts;
		return mm * 60 + ss;
	}
	if (parts.length === 3) {
		const [hh, mm, ss] = parts;
		return hh * 3600 + mm * 60 + ss;
	}
	return null;
}

function formatSecondsAsTimestamp(totalSeconds: number): string {
	const seconds = Math.max(0, Math.floor(totalSeconds));
	const mm = Math.floor(seconds / 60);
	const ss = seconds % 60;
	return `${mm}:${String(ss).padStart(2, "0")}`;
}

function generateTimestampedTranscriptForDefaultMock(
	transcript: TranscriptIn
): TimestampedTranscriptLine[] {
	// Split text into sentence-ish chunks and assign evenly-spaced timestamps.
	const chunks =
		transcript.text
			.match(/[^.!?]+[.!?]*/g)
			?.map((s) => s.trim())
			.filter(Boolean) ?? [];

	if (chunks.length === 0) {
		return [{ text: transcript.text, time: "0:01" }];
	}

	const totalSeconds = parseDurationToSeconds(transcript.duration);
	const hasUsableDuration =
		typeof totalSeconds === "number" && totalSeconds >= 2;

	let lastAssigned = 0;
	return chunks.map((text, idx) => {
		let seconds: number;

		if (hasUsableDuration) {
			// Spread timestamps across the call duration, starting at ~1s.
			const raw = Math.floor(((idx + 1) * totalSeconds!) / (chunks.length + 1));
			seconds = Math.max(1, raw);
		} else {
			// Fallback: 5-second increments.
			seconds = 1 + idx * 5;
		}

		// Ensure monotonic increasing times.
		seconds = Math.max(seconds, lastAssigned + 1);
		lastAssigned = seconds;

		return { text, time: formatSecondsAsTimestamp(seconds) };
	});
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
  const [error, setError] = useState<string | null>(null);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isResolving, setIsResolving] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [dispatcherLogs, setDispatcherLogs] = useState<LogEntry[]>([]);
  const [suppressedNotices, setSuppressedNotices] = useState<
    Array<{ id: string; duplicate_of?: string | null; notice?: string | null; createdAt: number }>
  >([]);
  
  // Counter for unique log IDs
  const logIdCounter = useRef(0);
  
  // Callback to add log entries from useDispatchers
  const handleLog = useCallback((message: string) => {
    const newLog: LogEntry = {
      id: `log-${logIdCounter.current++}`,
      timestamp: new Date(),
      message,
    };
    setDispatcherLogs((prev) => [...prev, newLog]);
  }, []);

  // Track IDs that have already been removed by user (idempotency guard)
  const userRemovedIdsRef = useRef<Set<string>>(new Set());
  const userRemoveInFlightRef = useRef<Set<string>>(new Set());

  // Guard to prevent double initialization in React strict mode
  const initGuardRef = useRef(false);

  // Safe polling: use visibility state to pause when tab is hidden
  const {
    data: queue,
    error: queueError,
    isPending: queueIsPending,
    refetch: refetchQueue,
  } = useQuery({
    queryKey: ["queue"],
    queryFn: ({ signal }) => fetchQueue(signal),
    refetchInterval: 1000,
    staleTime: 0,
    refetchIntervalInBackground: false, // Pause when tab hidden
    placeholderData: (previousData) => previousData, // Keep last good data
  });

  const { dispatchers, claimedQueueIds, pendingCurrentCallsCount } = useDispatchers(
    queue,
    config,
    selectedCallId,
    refetchQueue,
    handleLog
  );
  
  // Handle action button clicks from sidebar
  const handleActionClick = useCallback((action: string) => {
    setActionMessage(`${action} completed!`);
    handleLog(`[Action] ${action} triggered`);
    // Clear the message after 3 seconds
    setTimeout(() => setActionMessage(null), 3000);
  }, [handleLog]);

  // Filter queue to exclude claimed IDs (so user can't select them)
  const visibleQueue = useMemo(() => {
    if (!queue) return undefined;
    const filtered = queue.filter((item) => !claimedQueueIds.has(item.id));
    return filtered;
  }, [queue, claimedQueueIds]);

  // Load config and initialize simulation on mount
  useEffect(() => {
    const loadConfigAndInitialize = async () => {
      // Prevent double initialization in strict mode
      if (initGuardRef.current) return;
      initGuardRef.current = true;

      setIsInitializing(true);
      let loadedConfig: SimulationConfig = DEFAULT_CONFIG;
      let storedConfigRaw: string | null = null;

      try {
        storedConfigRaw = localStorage.getItem("simulationConfig");
        if (storedConfigRaw) {
          loadedConfig = { ...DEFAULT_CONFIG, ...JSON.parse(storedConfigRaw) };
        }
      } catch (e) {
        console.error(
          "Failed to parse config from localStorage, using defaults.",
          e
        );
      }

      setConfig(loadedConfig);

      // Always invoke on dashboard load.
      // Clear the cached queue so the Queue component can show skeletons during init.
      queryClient.removeQueries({ queryKey: ["queue"], exact: true });

      // Determine which transcripts to invoke
      let transcriptsToInvoke: TranscriptIn[] = [];
      const customIncomingCalls = loadedConfig.customIncomingCalls ?? [];
      const hasCustomIncomingCalls = customIncomingCalls.length > 0;

      if (hasCustomIncomingCalls) {
        // Use custom incoming calls (override defaults)
        console.log(
          `Using ${customIncomingCalls.length} custom incoming calls.`
        );
        transcriptsToInvoke = customIncomingCalls.map(
          (c: CustomCall) => c.transcript
        );
      } else if (loadedConfig.incomingCalls > 0) {
        // Use default mock transcripts
        console.log(
          `Using ${loadedConfig.incomingCalls} default incoming calls from mock data.`
        );
        transcriptsToInvoke = Array.from({ length: loadedConfig.incomingCalls }, () => {
          const randomIndex = Math.floor(Math.random() * mockTranscripts.length);
          return mockTranscripts[randomIndex];
        });
      }

      if (transcriptsToInvoke.length > 0) {
        console.log(
          `Sending ${transcriptsToInvoke.length} initial calls to backend...`
        );

        const invokePromises = transcriptsToInvoke.map((transcript) => {
          const timestamped_transcript: TimestampedTranscriptLine[] = hasCustomIncomingCalls
            ? [{ text: transcript.text, time: "0:15" }]
            : generateTimestampedTranscriptForDefaultMock(transcript);

          return invokeTranscript(transcript, timestamped_transcript);
        });

        try {
          const results = (await Promise.all(invokePromises)) as InvokeResponse[];
          const suppressed = results
            .filter((r) => r && r.enqueued === false && r.result?.id)
            .map((r) => ({
              id: r.result.id,
              duplicate_of: r.duplicate_of ?? null,
              notice: r.notice ?? null,
              createdAt: Date.now(),
            }));
          if (suppressed.length > 0) {
            setSuppressedNotices((prev) => {
              const existing = new Set(prev.map((p) => p.id));
              const merged = [...prev];
              for (const n of suppressed) {
                if (!existing.has(n.id)) merged.unshift(n);
              }
              return merged.slice(0, 50);
            });
          }
          console.log(
            `${transcriptsToInvoke.length} initial calls sent to backend.`
          );
          refetchQueue();
        } catch (e: unknown) {
          console.error("Initialization error:", e);
          const errorMessage =
            e instanceof Error ? e.message : "An unknown error occurred";
          setError(errorMessage);
        }
      }

      setIsInitializing(false);
    };

    loadConfigAndInitialize();
  }, [refetchQueue, queryClient]);

  const handleSelectCall = useCallback((id: string) => {
    setSelectedCallId((prevId) => (prevId === id ? null : id));
  }, []);

  const handleResolveCall = useCallback(
    async (id: string) => {
      // Idempotency guard: prevent duplicate removes
      if (
        userRemovedIdsRef.current.has(id) ||
        userRemoveInFlightRef.current.has(id)
      ) {
        console.log(`[User] Call ${id} already removed or in-flight, skipping.`);
        return;
      }

      userRemoveInFlightRef.current.add(id);
      setIsResolving(true);

      try {
        await removeFromQueue(id);
        console.log(`[User] Call ${id} resolved successfully.`);
        userRemovedIdsRef.current.add(id);
        setSelectedCallId(null);
        refetchQueue();
        queryClient.invalidateQueries({ queryKey: ["incidentDetails", id] });
      } catch (e: unknown) {
        console.error("[User] Error resolving call:", e);
        const errorMessage =
          e instanceof Error ? e.message : "Failed to resolve call.";
        setError(errorMessage);
      } finally {
        userRemoveInFlightRef.current.delete(id);
        setIsResolving(false);
      }
    },
    [refetchQueue, queryClient]
  );

  // Calculate counts for info display
  const customIncomingCount = config.customIncomingCalls?.length || 0;
  const customCurrentCount = config.customCurrentCalls?.length || 0;

  // Build info summary for header
  const infoSummary = [
    `${config.dispatchers} Dispatchers`,
    customIncomingCount > 0
      ? `${customIncomingCount} custom incoming`
      : `${config.incomingCalls} incoming`,
    `${config.handleTime === "random" ? "Random" : config.handleTime + "m"} handle`,
    customCurrentCount > 0 || config.initialBusyDispatchers > 0
      ? `${customCurrentCount > 0 ? customCurrentCount : config.initialBusyDispatchers} current`
      : null,
    pendingCurrentCallsCount > 0 ? `${pendingCurrentCallsCount} pending` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  return (
    <div className="flex flex-col h-screen font-sans bg-zinc-900 p-5">
      {/* Header with Info centered */}
      <div className="flex-shrink-0 flex flex-row w-full h-14 bg-zinc-800 p-3 items-center mb-3 rounded-lg justify-between">
        <div className="flex items-center">
          <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
          {isInitializing && (
            <span className="ml-4 text-sm text-zinc-400">
              Initializing...
            </span>
          )}
        </div>

        {/* Info summary centered */}
        <div className="flex-1 flex justify-center">
          <span className="text-zinc-400 text-sm">{infoSummary}</span>
        </div>

        <Link href="/" className="text-zinc-400 hover:text-white text-sm">
          ← Home
        </Link>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex-shrink-0 bg-red-900 text-white p-3 rounded-md mb-3">
          <p>
            <strong>Error:</strong> {error}
          </p>
          <button
            onClick={() => setError(null)}
            className="text-red-200 underline text-sm mt-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content: Queue (left) + Center Panel + Right Sidebar */}
      <div className="flex flex-row flex-1 w-full gap-3 overflow-hidden min-h-0">
        {/* Queue Panel - Left */}
        <div className="flex flex-col w-72 flex-shrink-0 bg-zinc-800 p-4 rounded-lg overflow-hidden">
          <h1 className="text-white font-bold text-xl mb-2 flex-shrink-0">
            Queue
          </h1>
          <div className="overflow-y-auto flex-1">
            <Queue
              data={isInitializing ? undefined : visibleQueue}
              isPending={queueIsPending || isInitializing}
              error={queueError}
              onSelectCall={handleSelectCall}
              selectedCallId={selectedCallId}
              suppressedNotices={suppressedNotices}
              onDismissSuppressed={(id) =>
                setSuppressedNotices((prev) => prev.filter((n) => n.id !== id))
              }
            />
          </div>
        </div>

        {/* Center Panel - Action Messages */}
        <div className="flex flex-col flex-1 bg-zinc-800 rounded-lg overflow-hidden">
          <div className="flex items-center justify-center h-full">
            {actionMessage ? (
              <div className="text-center">
                <div className="text-green-400 text-2xl font-bold mb-2">✓</div>
                <p className="text-white text-xl">{actionMessage}</p>
              </div>
            ) : (
              <p className="text-zinc-400 text-center">
                {selectedCallId
                  ? "Use the action buttons in the sidebar to take action on this call."
                  : "Select a call from the queue to get started."}
              </p>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="flex flex-col w-96 flex-shrink-0 overflow-hidden">
          <Sidebar
            incidentId={selectedCallId}
            onResolve={handleResolveCall}
            isResolving={isResolving}
            onActionClick={handleActionClick}
            logs={dispatcherLogs}
          />
        </div>
      </div>

      {/* Bottom: Dispatcher Status (scrollable) */}
      <div className="flex-shrink-0 mt-3 h-48 bg-zinc-800 rounded-lg overflow-hidden">
        <DispatcherStatus dispatchers={dispatchers} />
      </div>
    </div>
  );
}
