"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { QueueItem, removeFromQueue } from "@/lib/api";

// Define the shape of a dispatcher object
export interface Dispatcher {
  id: number;
  status: "idle" | "busy";
  callId: string | null;
  endTime: number | null;
  isInitialBusy: boolean; // True if this is an initial "current call" (client-only)
}

// Define the shape of the simulation configuration
export interface SimulationConfig {
  dispatchers: number;
  incomingCalls: number;
  handleTime: string; // '1', '3', '5', or 'random'
  initialBusyDispatchers: number;
  initialBusyHandleTime: string;
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

  // Track IDs that have already had DELETE called (idempotency guard)
  const removedIdsRef = useRef<Set<string>>(new Set());
  // Track IDs currently being removed (in-flight guard)
  const removeInFlightRef = useRef<Set<string>>(new Set());

  // Use a ref to keep track of the latest queue without re-triggering the effect
  const queueRef = useRef(queue);
  queueRef.current = queue;

  // Initialize dispatchers
  useEffect(() => {
    const now = Date.now();
    const initialDispatchers: Dispatcher[] = Array.from(
      { length: config.dispatchers },
      (_, i) => {
        const dispatcherId = i + 1;
        const isInitialBusy = i < config.initialBusyDispatchers;

        if (isInitialBusy) {
          // Initial busy dispatchers are client-only placeholders
          return {
            id: dispatcherId,
            status: "busy" as const,
            callId: null, // No real call ID - this is a client-side placeholder
            endTime: now + getHandleDuration(config.initialBusyHandleTime),
            isInitialBusy: true,
          };
        }

        return {
          id: dispatcherId,
          status: "idle" as const,
          callId: null,
          endTime: null,
          isInitialBusy: false,
        };
      }
    );
    setDispatchers(initialDispatchers);
    // Reset claimed IDs on config change
    setClaimedQueueIds(new Set());
    removedIdsRef.current = new Set();
    removeInFlightRef.current = new Set();
  }, [config.dispatchers, config.initialBusyDispatchers, config.initialBusyHandleTime]);

  const processDispatchers = useCallback(() => {
    const currentQueue = queueRef.current;

    setDispatchers((prevDispatchers) => {
      const newDispatchers = [...prevDispatchers];
      const newClaimedIds = new Set(claimedQueueIds);
      let shouldRefetch = false;

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
              dispatcher.isInitialBusy ? "initial busy" : `call ${dispatcher.callId}`
            }`
          );

          // If this was a real queue call (not initial busy), send DELETE
          if (!dispatcher.isInitialBusy && dispatcher.callId) {
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
            isInitialBusy: false,
          };
        }
      }

      // Second pass: check if any idle dispatcher can pick a call
      if (currentQueue && currentQueue.length > 0) {
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
                `[Dispatcher ${dispatcher.id}] claiming call ${availableCall.id}`
              );

              newDispatchers[i] = {
                ...dispatcher,
                status: "busy",
                callId: availableCall.id,
                endTime: Date.now() + getHandleDuration(config.handleTime),
                isInitialBusy: false,
              };

              shouldRefetch = true;
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
  }, [config.handleTime, selectedCallId, claimedQueueIds, refetchQueue]);

  useEffect(() => {
    const interval = setInterval(processDispatchers, 1000); // Check every second
    return () => clearInterval(interval);
  }, [processDispatchers]);

  return { dispatchers, claimedQueueIds };
}
