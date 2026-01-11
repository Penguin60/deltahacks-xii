"use client";

import { useEffect, useState, useRef, useCallback } from 'react';

// Define the shape of a queue item based on backend/main.py's queue_entry
interface QueueItem {
    id: string;
    incidentType: string;
    location: string;
    time: string;
    severity_level: string;
    suggested_actions: string;
}

// Define the shape of the dispatcher object
interface Dispatcher {
    id: number;
    status: 'idle' | 'busy';
    callId: string | null;
    endTime: number | null; // Timestamp when the dispatcher becomes idle
}

// Define the shape of the simulation configuration
interface SimulationConfig {
    dispatchers: number;
    incomingCalls: number; // Not directly used here, but part of overall config
    handleTime: string; // '1', '3', '5', or 'random'
}

// Helper to convert handleTime string to actual seconds
const getHandleDuration = (handleTime: string): number => {
    switch (handleTime) {
        case '1': return 60 * 1000; // 1 minute
        case '3': return 3 * 60 * 1000; // 3 minutes
        case '5': return 5 * 60 * 1000; // 5 minutes
        case 'random':
            const durations = [1, 3, 5];
            const randomMin = durations[Math.floor(Math.random() * durations.length)];
            return randomMin * 60 * 1000;
        default: return 3 * 60 * 1000; // Default to 3 minutes
    }
};

interface UseDispatcherReturn {
    dispatchers: Dispatcher[];
}

export function useDispatchers(
    queue: QueueItem[] | undefined,
    config: SimulationConfig,
    selectedCallId: string | null,
    refetchQueue: () => void
): UseDispatcherReturn {
    const [dispatchers, setDispatchers] = useState<Dispatcher[]>([]);
    // Use a ref to keep track of the latest queue without re-triggering the effect
    const queueRef = useRef(queue);
    queueRef.current = queue;

    // Initialize dispatchers
    useEffect(() => {
        setDispatchers(
            Array.from({ length: config.dispatchers }, (_, i) => ({
                id: i + 1,
                status: 'idle',
                callId: null,
                endTime: null,
            }))
        );
    }, [config.dispatchers]);

    const processDispatchers = useCallback(() => {
        const currentQueue = queueRef.current;
        if (!currentQueue || currentQueue.length === 0) return;

        setDispatchers(prevDispatchers => {
            const newDispatchers = [...prevDispatchers];
            const claimedInThisTick = new Set<string>();
            let queueNeedsRefetch = false;

            for (let i = 0; i < newDispatchers.length; i++) {
                const dispatcher = newDispatchers[i];

                // Check if busy dispatcher is done
                if (dispatcher.status === 'busy' && dispatcher.endTime && Date.now() >= dispatcher.endTime) {
                    console.log(`[Dispatcher ${dispatcher.id}] finished call ${dispatcher.callId}`);
                    newDispatchers[i] = { ...dispatcher, status: 'idle', callId: null, endTime: null };
                }
            }

            for (let i = 0; i < newDispatchers.length; i++) {
                const dispatcher = newDispatchers[i];

                // Check if dispatcher is idle and can take a call
                if (dispatcher.status === 'idle') {
                    // Find a call that isn't selected by the user and hasn't been claimed this tick
                    const availableCall = currentQueue.find(
                        call => call.id !== selectedCallId && !claimedInThisTick.has(call.id)
                    );

                    if (availableCall) {
                        claimedInThisTick.add(availableCall.id); // Mark as claimed for this tick

                        // Optimistically update dispatcher state
                        newDispatchers[i] = {
                            ...dispatcher,
                            status: 'busy',
                            callId: availableCall.id,
                            endTime: Date.now() + getHandleDuration(config.handleTime),
                        };
                        
                        console.log(`[Dispatcher ${dispatcher.id}] attempting to claim call ${availableCall.id}`);

                        fetch(`http://localhost:8000/remove/${availableCall.id}`, { method: 'DELETE' })
                            .then(response => {
                                if (!response.ok) {
                                    // This can happen in a race condition, but it's less likely now.
                                    // We just log it instead of throwing a disruptive error.
                                    console.warn(`[Dispatcher ${dispatcher.id}] failed to claim call ${availableCall.id}, backend status: ${response.status}. Another dispatcher might have taken it.`);
                                    // Revert the optimistic state update
                                    setDispatchers(current => current.map(d => d.id === dispatcher.id ? { ...d, status: 'idle', callId: null, endTime: null } : d));
                                } else {
                                    console.log(`[Dispatcher ${dispatcher.id}] successfully claimed call ${availableCall.id}`);
                                    queueNeedsRefetch = true;
                                }
                            });
                    }
                }
            }
            
            // A single refetch is enough if any call was successfully claimed.
            if(queueNeedsRefetch) {
                refetchQueue();
            }
            
            return newDispatchers;
        });
    }, [config.handleTime, selectedCallId, refetchQueue]);

    useEffect(() => {
        const interval = setInterval(processDispatchers, 1000); // Check every second
        return () => clearInterval(interval);
    }, [processDispatchers]);

    return { dispatchers };
}

