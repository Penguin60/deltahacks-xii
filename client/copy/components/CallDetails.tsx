"use client";

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Transcript from './Transcript'; // Refactored Transcript component
import { Button } from '@/components/ui/button'; // Import Button component

// Based on backend/schemas.py TriageIncident and AgentState's timestamped_transcript
interface TranscriptLineData {
  text: string;
  time: string;
}

interface FullIncidentDetails {
    id: string;
    incidentType: string;
    location: string;
    date: string;
    time: string;
    duration: string;
    message: string;
    desc: string;
    suggested_actions: string;
    status: string;
    severity_level: string;
    transcript?: TranscriptLineData[]; // Optional as it might be added later
}

interface CallDetailsProps {
    incidentId: string | null;
    onResolve: (id: string) => void; // Add onResolve prop
}

const CallDetails: React.FC<CallDetailsProps> = ({ incidentId, onResolve }) => {
    const { data, isPending, error } = useQuery<FullIncidentDetails>({
        queryKey: ['incidentDetails', incidentId],
        queryFn: async () => {
            if (!incidentId) return Promise.reject(new Error("No incident ID provided."));
            const response = await fetch(`http://localhost:8000/agent/${incidentId}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch incident details');
            }
            const result = await response.json();
            return result.result; // Backend returns {"result": incident_object}
        },
        enabled: !!incidentId, // Only run query if incidentId is not null
        staleTime: Infinity, // Incident details don't change often
    });

    if (!incidentId) {
        return (
            <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-zinc-400">
                Select a call from the queue to view details.
            </div>
        );
    }

    if (isPending) {
        return (
            <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-white">
                Loading call details...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-zinc-800 rounded-lg h-full text-red-400">
                Error: {error.message}
            </div>
        );
    }

    if (!data) {
        return (
            <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-zinc-400">
                Incident not found.
            </div>
        );
    }

    return (
        <div className="p-4 bg-zinc-800 rounded-lg h-full overflow-y-auto">
            <h2 className="text-white font-bold text-xl mb-3">Call Details: {data.id.substring(0, 8)}...</h2>
            <div className="text-zinc-300 text-sm space-y-1 mb-4">
                <p><strong>Type:</strong> {data.incidentType}</p>
                <p><strong>Location:</strong> {data.location}</p>
                <p><strong>Date:</strong> {data.date}</p>
                <p><strong>Time:</strong> {data.time}</p>
                <p><strong>Duration:</strong> {data.duration}</p>
                <p><strong>Severity:</strong> {data.severity_level}</p>
                <p><strong>Description:</strong> {data.desc}</p>
                <p><strong>Suggested Action:</strong> {data.suggested_actions}</p>
                <p><strong>Status:</strong> {data.status}</p>
            </div>
            {data.transcript && data.transcript.length > 0 && (
                <div className="mt-4">
                    <h3 className="text-white font-semibold text-lg mb-2">Transcript</h3>
                    <Transcript transcript={data.transcript} />
                </div>
            )}
            <Button 
                onClick={() => onResolve(data.id)} 
                className="mt-4 w-full bg-green-600 hover:bg-green-700"
                disabled={data.status === 'completed'} // Disable if already completed
            >
                {data.status === 'completed' ? 'Resolved' : 'Resolve Call'}
            </Button>
        </div>
    );
};

export default CallDetails;

