"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Queue from "@/components/Queue";
import DispatcherStatus from "@/components/DispatcherStatus";
import CallDetails from "@/components/CallDetails";
import { mockTranscripts } from "@/lib/mock-data";
import { useDispatchers, SimulationConfig } from "@/hooks/useDispatchers";
import { fetchQueue, invokeTranscript, removeFromQueue, QueueItem } from "@/lib/api";
import Link from "next/link";

const DEFAULT_CONFIG: SimulationConfig = {
  dispatchers: 5,
  incomingCalls: 10,
  handleTime: "3",
  initialBusyDispatchers: 0,
  initialBusyHandleTime: "1",
};

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
  const [error, setError] = useState<string | null>(null);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isResolving, setIsResolving] = useState(false);

  // Track IDs that have already been removed by user (idempotency guard)
  const userRemovedIdsRef = useRef<Set<string>>(new Set());
  const userRemoveInFlightRef = useRef<Set<string>>(new Set());

  // Session guard to prevent re-invoking on refresh
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

  const { dispatchers, claimedQueueIds } = useDispatchers(
    queue,
    config,
    selectedCallId,
    refetchQueue
  );

  // Filter queue to exclude claimed IDs (so user can't select them)
  const visibleQueue = useMemo(() => {
    if (!queue) return undefined;
    return queue.filter((item) => !claimedQueueIds.has(item.id));
  }, [queue, claimedQueueIds]);

  // Load config and initialize simulation on mount
  useEffect(() => {
    const loadConfigAndInitialize = async () => {
      // Prevent double initialization in strict mode
      if (initGuardRef.current) return;
      initGuardRef.current = true;

      setIsInitializing(true);
      let loadedConfig: SimulationConfig = DEFAULT_CONFIG;

      try {
        const storedConfig = localStorage.getItem("simulationConfig");
        if (storedConfig) {
          loadedConfig = JSON.parse(storedConfig);
        }
      } catch (e) {
        console.error(
          "Failed to parse config from localStorage, using defaults.",
          e
        );
      }
      setConfig(loadedConfig);

      // Session guard: check if we've already initialized this session
      const sessionKey = `simulation_init_${JSON.stringify(loadedConfig)}`;
      const alreadyInitialized = sessionStorage.getItem(sessionKey);

      if (!alreadyInitialized && loadedConfig.incomingCalls > 0) {
        console.log(
          `Sending ${loadedConfig.incomingCalls} initial calls to backend...`
        );

        const invokePromises = Array.from(
          { length: loadedConfig.incomingCalls },
          () => {
            const randomIndex = Math.floor(
              Math.random() * mockTranscripts.length
            );
            const transcriptToSend = mockTranscripts[randomIndex];
            return invokeTranscript(transcriptToSend);
          }
        );

        try {
          await Promise.all(invokePromises);
          console.log(
            `${loadedConfig.incomingCalls} initial calls sent to backend.`
          );
          // Mark as initialized for this session
          sessionStorage.setItem(sessionKey, "true");
          refetchQueue();
        } catch (e: unknown) {
          console.error("Initialization error:", e);
          const errorMessage =
            e instanceof Error ? e.message : "An unknown error occurred";
          setError(errorMessage);
        }
      } else if (alreadyInitialized) {
        console.log("Session already initialized, skipping invoke calls.");
      }

      setIsInitializing(false);
    };

    loadConfigAndInitialize();
  }, [refetchQueue]);

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

  return (
    <div className="flex flex-col h-screen font-sans bg-zinc-900 p-5">
      {/* Header */}
      <div className="flex-shrink-0 flex flex-row w-full h-12 bg-zinc-800 p-3 items-center mb-3 rounded-lg justify-between">
        <div className="flex items-center">
          <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
          {isInitializing && (
            <span className="ml-4 text-sm text-zinc-400">
              Initializing calls...
            </span>
          )}
        </div>
        <Link href="/" className="text-zinc-400 hover:text-white text-sm">
          ← Back to Home
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

      {/* Main Content */}
      <div className="flex flex-row flex-1 w-full gap-3 overflow-hidden">
        {/* Queue Panel */}
        <div className="flex flex-col flex-1 bg-zinc-800 flex-[1.5] p-4 rounded-lg overflow-hidden">
          <h1 className="text-white font-bold text-xl mb-2 flex-shrink-0">
            Queue
          </h1>
          <div className="overflow-y-auto h-full">
            <Queue
              data={visibleQueue}
              isPending={queueIsPending}
              error={queueError}
              onSelectCall={handleSelectCall}
              selectedCallId={selectedCallId}
            />
          </div>
        </div>

        {/* Middle Panel: Dispatcher Status + Call Details */}
        <div className="flex flex-col flex-1 flex-[4] gap-3 overflow-hidden">
          <div className="flex flex-[5] bg-zinc-800 rounded-lg overflow-hidden">
            <DispatcherStatus dispatchers={dispatchers} />
          </div>
          <div className="flex flex-[2.5] bg-zinc-800 rounded-lg overflow-hidden">
            <CallDetails
              incidentId={selectedCallId}
              onResolve={handleResolveCall}
              isResolving={isResolving}
            />
          </div>
        </div>

        {/* Right Panel: Info */}
        <div className="flex flex-col flex-1 bg-zinc-800 flex-[2] p-4 rounded-lg">
          <h1 className="text-white font-bold text-xl">Info</h1>
          <div className="text-zinc-400 mt-4 text-sm space-y-2">
            <p>
              <strong>Dispatchers:</strong> {config.dispatchers}
            </p>
            <p>
              <strong>Initial Calls:</strong> {config.incomingCalls}
            </p>
            <p>
              <strong>Handle Time:</strong>{" "}
              {config.handleTime === "random"
                ? "Random (1/3/5 min)"
                : `${config.handleTime} min`}
            </p>
            {config.initialBusyDispatchers > 0 && (
              <>
                <p>
                  <strong>Initial Busy:</strong> {config.initialBusyDispatchers}
                </p>
                <p>
                  <strong>Busy Handle Time:</strong>{" "}
                  {config.initialBusyHandleTime === "random"
                    ? "Random"
                    : `${config.initialBusyHandleTime} min`}
                </p>
              </>
            )}
            <hr className="border-zinc-600 my-3" />
            <p className="text-zinc-500">
              Select a call from the queue to view its full details. Dispatchers
              will automatically claim calls when they become idle.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
