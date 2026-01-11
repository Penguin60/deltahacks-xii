"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { QueueItem, removeFromQueue } from "@/lib/api";
import { generateUlid } from "@/lib/ulid";

// TranscriptIn shape (matches backend)
export interface TranscriptIn {
  text: string;
  time: string;
  location: string;
  duration: string;
}

// Custom call with client ID
export interface CustomCall {
  clientId: string;
  transcript: TranscriptIn;
}

// Define the shape of a dispatcher object
export interface Dispatcher {
  id: number;
  status: "idle" | "busy";
  callId: string | null; // For queue calls: backend ID. For current calls: clientId.
  endTime: number | null;
  isCurrentCall: boolean; // True if this is a current call (client-only, no backend interaction)
}

// Define the shape of the simulation configuration
export interface SimulationConfig {
  dispatchers: number;
  incomingCalls: number;
  handleTime: string; // '1', '3', '5', or 'random'
  initialBusyDispatchers: number;
  initialBusyHandleTime: string;
  customIncomingCalls?: CustomCall[];
  customCurrentCalls?: CustomCall[];
}

// Helper to convert handleTime string to actual milliseconds
const getHandleDuration = (handleTime: string): number => {
  switch (handleTime) {
    case "1":
      return 60 * 1000; // 1 minute
    case "3":
      return 3 * 60 * 1000; // 3 minutes
    case "5":
      return 5 * 60 * 1000; // 5 minutes
    case "random":
      const durations = [1, 3, 5];
      const randomMin = durations[Math.floor(Math.random() * durations.length)];
      return randomMin * 60 * 1000;
    default:
      return 3 * 60 * 1000; // Default to 3 minutes
  }
};

interface UseDispatcherReturn {
  dispatchers: Dispatcher[];
  claimedQueueIds: Set<string>;
  pendingCurrentCallsCount: number;
}

export function useDispatchers(
  queue: QueueItem[] | undefined,
  config: SimulationConfig,
  selectedCallId: string | null,
  refetchQueue: () => void
): UseDispatcherReturn {
  const [dispatchers, setDispatchers] = useState<Dispatcher[]>([]);
  const [claimedQueueIds, setClaimedQueueIds] = useState<Set<string>>(
    new Set()
  );
  // Queue of pending current calls (client-only) waiting for a dispatcher
  const [pendingCurrentCalls, setPendingCurrentCalls] = useState<CustomCall[]>([]);

  // Track IDs that have already had DELETE called (idempotency guard)
  const removedIdsRef = useRef<Set<string>>(new Set());
  // Track IDs currently being removed (in-flight guard)
  const removeInFlightRef = useRef<Set<string>>(new Set());

  // Use a ref to keep track of the latest queue without re-triggering the effect
  const queueRef = useRef(queue);
  queueRef.current = queue;

  // Initialize dispatchers and current calls queue
  useEffect(() => {
    const now = Date.now();

    // Determine current calls to use
    let currentCallsList: CustomCall[] = [];
    if (config.customCurrentCalls && config.customCurrentCalls.length > 0) {
      // Use custom current calls
      currentCallsList = [...config.customCurrentCalls];
    } else if (config.initialBusyDispatchers > 0) {
      // Generate default current calls with ULIDs
      currentCallsList = Array.from({ length: config.initialBusyDispatchers }, () => ({
        clientId: generateUlid(),
        transcript: {
          text: "Initial busy call (simulated)",
          time: new Date().toISOString(),
          location: "N/A",
          duration: "00:00",
        },
      }));
    }

    // Assign current calls to dispatchers, queue overflow
    const initialDispatchers: Dispatcher[] = [];
    const overflowCurrentCalls: CustomCall[] = [];

    for (let i = 0; i < config.dispatchers; i++) {
      const dispatcherId = i + 1;
      const currentCall = currentCallsList[i];

      if (currentCall) {
        // This dispatcher starts busy with a current call
        initialDispatchers.push({
          id: dispatcherId,
          status: "busy",
          callId: currentCall.clientId,
          endTime: now + getHandleDuration(config.initialBusyHandleTime),
          isCurrentCall: true,
        });
      } else {
        // This dispatcher starts idle
        initialDispatchers.push({
          id: dispatcherId,
          status: "idle",
          callId: null,
          endTime: null,
          isCurrentCall: false,
        });
      }
    }

    // Any remaining current calls beyond dispatcher count go to overflow queue
    if (currentCallsList.length > config.dispatchers) {
      overflowCurrentCalls.push(...currentCallsList.slice(config.dispatchers));
    }

    setDispatchers(initialDispatchers);
    setPendingCurrentCalls(overflowCurrentCalls);
    // Reset claimed IDs on config change
    setClaimedQueueIds(new Set());
    removedIdsRef.current = new Set();
    removeInFlightRef.current = new Set();
  }, [
    config.dispatchers,
    config.initialBusyDispatchers,
    config.initialBusyHandleTime,
    config.customCurrentCalls,
  ]);

  const processDispatchers = useCallback(() => {
    const currentQueue = queueRef.current;

    setDispatchers((prevDispatchers) => {
      const newDispatchers = [...prevDispatchers];
      const newClaimedIds = new Set(claimedQueueIds);

      // First pass: check if any busy dispatchers are done
      for (let i = 0; i < newDispatchers.length; i++) {
        const dispatcher = newDispatchers[i];

        if (
          dispatcher.status === "busy" &&
          dispatcher.endTime &&
          Date.now() >= dispatcher.endTime
        ) {
          console.log(
            `[Dispatcher ${dispatcher.id}] finished ${
              dispatcher.isCurrentCall ? `current call ${dispatcher.callId}` : `queue call ${dispatcher.callId}`
            }`
          );

          // If this was a queue call (not current call), send DELETE
          if (!dispatcher.isCurrentCall && dispatcher.callId) {
            const callIdToRemove = dispatcher.callId;

            // Idempotency check: only remove if not already removed or in-flight
            if (
              !removedIdsRef.current.has(callIdToRemove) &&
              !removeInFlightRef.current.has(callIdToRemove)
            ) {
              removeInFlightRef.current.add(callIdToRemove);

              removeFromQueue(callIdToRemove)
                .then(() => {
                  console.log(
                    `[Dispatcher ${dispatcher.id}] successfully removed call ${callIdToRemove} from backend`
                  );
                  removedIdsRef.current.add(callIdToRemove);
                  // Remove from claimed set
                  setClaimedQueueIds((prev) => {
                    const updated = new Set(prev);
                    updated.delete(callIdToRemove);
                    return updated;
                  });
                  refetchQueue();
                })
                .catch((err) => {
                  console.warn(
                    `[Dispatcher ${dispatcher.id}] failed to remove call ${callIdToRemove}:`,
                    err
                  );
                })
                .finally(() => {
                  removeInFlightRef.current.delete(callIdToRemove);
                });
            }
          }

          // Reset dispatcher to idle
          newDispatchers[i] = {
            ...dispatcher,
            status: "idle",
            callId: null,
            endTime: null,
            isCurrentCall: false,
          };
        }
      }

      // Second pass: idle dispatchers pick from pending current calls first
      setPendingCurrentCalls((prevPending) => {
        if (prevPending.length === 0) return prevPending;

        const remainingPending = [...prevPending];
        const now = Date.now();

        for (let i = 0; i < newDispatchers.length; i++) {
          const dispatcher = newDispatchers[i];

          if (dispatcher.status === "idle" && remainingPending.length > 0) {
            const nextCurrentCall = remainingPending.shift()!;

            console.log(
              `[Dispatcher ${dispatcher.id}] picking up queued current call ${nextCurrentCall.clientId}`
            );

            newDispatchers[i] = {
              ...dispatcher,
              status: "busy",
              callId: nextCurrentCall.clientId,
              endTime: now + getHandleDuration(config.initialBusyHandleTime),
              isCurrentCall: true,
            };
          }
        }

        return remainingPending;
      });

      // Third pass: only if no pending current calls, idle dispatchers pick from queue
      // Check if there are still pending current calls
      // Note: we use a ref-like check since setPendingCurrentCalls is async
      // For now, we'll block queue pickup if any dispatcher is handling a current call
      // or if there might be pending ones (conservative approach)
      const hasCurrentCallsActive = newDispatchers.some((d) => d.isCurrentCall);

      if (!hasCurrentCallsActive && currentQueue && currentQueue.length > 0) {
        for (let i = 0; i < newDispatchers.length; i++) {
          const dispatcher = newDispatchers[i];

          if (dispatcher.status === "idle") {
            // Find a call that:
            // 1. Is not selected by the user
            // 2. Has not been claimed by another dispatcher
            // 3. Has not been removed already
            const availableCall = currentQueue.find(
              (call) =>
                call.id !== selectedCallId &&
                !newClaimedIds.has(call.id) &&
                !removedIdsRef.current.has(call.id)
            );

            if (availableCall) {
              // Claim this call immediately (client-side)
              newClaimedIds.add(availableCall.id);

              console.log(
                `[Dispatcher ${dispatcher.id}] claiming queue call ${availableCall.id}`
              );

              newDispatchers[i] = {
                ...dispatcher,
                status: "busy",
                callId: availableCall.id,
                endTime: Date.now() + getHandleDuration(config.handleTime),
                isCurrentCall: false,
              };
            }
          }
        }
      }

      // Update claimed IDs state
      if (newClaimedIds.size !== claimedQueueIds.size) {
        setClaimedQueueIds(newClaimedIds);
      }

      return newDispatchers;
    });
  }, [config.handleTime, config.initialBusyHandleTime, selectedCallId, claimedQueueIds, refetchQueue]);

  useEffect(() => {
    const interval = setInterval(processDispatchers, 1000); // Check every second
    return () => clearInterval(interval);
  }, [processDispatchers]);

  return { dispatchers, claimedQueueIds, pendingCurrentCallsCount: pendingCurrentCalls.length };
}
