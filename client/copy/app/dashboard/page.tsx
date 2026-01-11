"use client";

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Queue from "@/components/Queue";
import DispatcherStatus from '@/components/DispatcherStatus';
import CallDetails from '@/components/CallDetails';
import { mockTranscripts, TranscriptIn } from '@/lib/mock-data';
import { useDispatchers } from '@/hooks/useDispatchers';

interface SimulationConfig {
    dispatchers: number;
    incomingCalls: number;
    handleTime: string;
}

const DEFAULT_CONFIG: SimulationConfig = {
    dispatchers: 5,
    incomingCalls: 10,
    handleTime: '3',
};

async function sendInvokeRequest(transcript: TranscriptIn) {
    try {
        const response = await fetch('http://localhost:8000/invoke', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Failed to invoke backend: ${errorData.detail || response.statusText}`);
        }
    } catch (error) {
        console.error('Error invoking backend:', error);
    }
}

export default function DashboardPage() {
    const router = useRouter();
    const queryClient = useQueryClient();
    const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
    const [error, setError] = useState<string | null>(null);
    const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);

    const { data: queue, error: queueError, isPending: queueIsPending, refetch: refetchQueue } = useQuery({
        queryKey: ["repoData"],
        queryFn: () => fetch("http://localhost:8000/queue").then((res) => res.json()),
        refetchInterval: 1000, // Slightly slower refetch to reduce load
        staleTime: 0,
    });

    const { dispatchers } = useDispatchers(queue, config, selectedCallId, refetchQueue);

    useEffect(() => {
        const loadConfigAndInitialize = async () => {
            setIsInitializing(true);
            let loadedConfig: SimulationConfig = DEFAULT_CONFIG;
            try {
                const storedConfig = localStorage.getItem('simulationConfig');
                if (storedConfig) {
                    loadedConfig = JSON.parse(storedConfig);
                }
            } catch (e) {
                console.error("Failed to parse config from localStorage, using defaults.", e);
            }
            setConfig(loadedConfig);

            // Fire-and-forget the initialization
            const invokePromises = Array.from({ length: loadedConfig.incomingCalls }, () => {
                const randomIndex = Math.floor(Math.random() * mockTranscripts.length);
                const transcriptToSend = mockTranscripts[randomIndex];
                return sendInvokeRequest(transcriptToSend);
            });

            try {
                await Promise.all(invokePromises);
                console.log(`${loadedConfig.incomingCalls} initial calls sent to backend.`);
                refetchQueue();
            } catch (e: any) {
                console.error("Initialization error:", e);
                setError(e.message || "An unknown error occurred during initialization.");
            } finally {
                setIsInitializing(false); // Stop initialization state
            }
        };

        loadConfigAndInitialize();
    }, [refetchQueue]);

    const handleSelectCall = useCallback((id: string) => {
        setSelectedCallId(prevId => (prevId === id ? null : id));
    }, []);

    const handleResolveCall = useCallback(async (id: string) => {
        try {
            const response = await fetch(`http://localhost:8000/remove/${id}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Failed to resolve call: ${errorData.detail || response.statusText}`);
            }
            console.log(`Call ${id} resolved successfully.`);
            setSelectedCallId(null);
            refetchQueue();
            queryClient.invalidateQueries({ queryKey: ['incidentDetails', id] });
        } catch (e: any) {
            console.error("Error resolving call:", e);
            setError(e.message || "Failed to resolve call.");
        }
    }, [refetchQueue, queryClient]);

    return (
        <div className="flex flex-col h-screen font-sans bg-zinc-900 p-5">
            <div className="flex-shrink-0 flex flex-row w-full h-12 bg-zinc-800 p-3 items-center mb-3 rounded-lg">
                <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
                 {isInitializing && <span className="ml-4 text-sm text-zinc-400">Initializing calls...</span>}
            </div>
            {error && (
                 <div className="flex-shrink-0 bg-red-900 text-white p-3 rounded-md mb-3">
                    <p><strong>Error:</strong> {error}</p>
                 </div>
            )}
            <div className="flex flex-row flex-1 w-full gap-3 overflow-hidden">
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[1.5] p-4 rounded-lg overflow-y-auto">
                    <h1 className="text-white font-bold text-xl mb-2 flex-shrink-0">Queue</h1>
                    <div className="overflow-y-auto h-full">
                        <Queue 
                            data={queue} 
                            isPending={queueIsPending}
                            error={queueError}
                            onSelectCall={handleSelectCall} 
                            selectedCallId={selectedCallId} 
                        />
                    </div>
                </div>
                <div className="flex flex-col flex-1 flex-[4] gap-3">
                    <div className="flex flex-[5] bg-zinc-800 rounded-lg">
                        <DispatcherStatus dispatchers={dispatchers} />
                    </div>
                    <div className="flex flex-[2.5] bg-zinc-800 rounded-lg">
                        <CallDetails incidentId={selectedCallId} onResolve={handleResolveCall} />
                    </div>
                </div>
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[2] p-4 rounded-lg">
                    <h1 className="text-white font-bold text-xl">Details</h1>
                     <div className="text-zinc-400 mt-4">
                        Select a call to see its full transcript and details in the middle panel.
                    </div>
                </div>
            </div>
        </div>
    );
}

