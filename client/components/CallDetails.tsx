"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchIncidentDetails } from "@/lib/api";
import { Button } from "@/components/ui/button";
import Transcript from "./Transcript";
import { getIdSuffix } from "@/lib/ulid";

interface CallDetailsProps {
  incidentId: string | null;
  onResolve: (id: string) => void;
  isResolving?: boolean;
}

const CallDetails: React.FC<CallDetailsProps> = ({
  incidentId,
  onResolve,
  isResolving = false,
}) => {
  const { data, isPending, error } = useQuery({
    queryKey: ["incidentDetails", incidentId],
    queryFn: async () => {
      if (!incidentId) {
        throw new Error("No incident ID provided.");
      }
      return fetchIncidentDetails(incidentId);
    },
    enabled: !!incidentId,
    staleTime: Infinity, // Incident details don't change often
  });

  if (!incidentId) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-zinc-400 w-full">
        Select a call from the queue to view details.
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-white w-full">
        Loading call details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg h-full text-red-400 w-full">
        Error: {error.message}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg h-full flex items-center justify-center text-zinc-400 w-full">
        Incident not found.
      </div>
    );
  }

  return (
    <div className="p-4 bg-zinc-800 rounded-lg h-full overflow-y-auto w-full">
      <h2 className="text-white font-bold text-xl mb-3">
        Call Details: ...{getIdSuffix(data.id, 8)}
      </h2>
      <div className="text-zinc-300 text-sm space-y-1 mb-4">
        <p>
          <strong>Type:</strong> {data.incidentType}
        </p>
        <p>
          <strong>Location:</strong> {data.location}
        </p>
        <p>
          <strong>Date:</strong> {data.date}
        </p>
        <p>
          <strong>Time:</strong> {data.time}
        </p>
        <p>
          <strong>Duration:</strong> {data.duration}
        </p>
        <p>
          <strong>Severity:</strong> {data.severity_level}
        </p>
        <p>
          <strong>Description:</strong> {data.desc}
        </p>
        <p>
          <strong>Suggested Action:</strong> {data.suggested_actions}
        </p>
        <p>
          <strong>Status:</strong> {data.status}
        </p>
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
        disabled={data.status === "completed" || isResolving}
      >
        {isResolving
          ? "Resolving..."
          : data.status === "completed"
          ? "Resolved"
          : "Resolve Call"}
      </Button>
    </div>
  );
};

export default CallDetails;
