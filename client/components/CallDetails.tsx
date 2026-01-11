"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchIncidentDetails } from "@/lib/api";
import { PhoneOff } from "lucide-react";

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
      <div className="flex flex-col items-center justify-center w-full h-full py-12 text-zinc-400 bg-zinc-800 rounded-lg">
        Select a call from the queue to view details.
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full py-12 text-white bg-zinc-800 rounded-lg">
        Loading call details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full py-12 text-red-400 bg-zinc-800 rounded-lg">
        Error: {error.message}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full py-12 text-zinc-400 bg-zinc-800 rounded-lg">
        Incident not found.
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-start w-full h-full py-12 text-white bg-zinc-800 rounded-lg overflow-y-auto">
      <div className="text-5xl font-extrabold tracking-tight">
        {data.incidentType}
      </div>
      <div className="mt-1 text-lg font-semibold text-zinc-300">
        {data.location}
      </div>

      <div className="mt-3 flex gap-2 flex-wrap justify-center">
        <span className="px-3 py-1 rounded-full bg-zinc-700 text-sm text-zinc-200">
          {data.date}
        </span>
        <span className="px-3 py-1 rounded-full bg-zinc-700 text-sm text-zinc-200">
          {data.time}
        </span>
        <span className="px-3 py-1 rounded-full bg-zinc-700 text-sm text-zinc-200">
          Severity: {data.severity_level}
        </span>
        <span className="px-3 py-1 rounded-full bg-zinc-700 text-sm text-zinc-200">
          {data.status}
        </span>
      </div>

      <p className="mt-5 max-w-3xl text-center text-base leading-relaxed text-zinc-100 px-4">
        {data.desc}
      </p>

      <p className="mt-4 max-w-3xl text-center text-sm leading-relaxed text-zinc-300 px-4">
        <strong>Suggested Action:</strong> {data.suggested_actions}
      </p>

      <button
        onClick={() => onResolve(data.id)}
        disabled={data.status === "completed" || isResolving}
        className="mt-8 w-14 h-14 rounded-full bg-red-700 hover:bg-red-800 disabled:bg-zinc-600 disabled:cursor-not-allowed flex items-center justify-center shadow-lg transition-colors"
        aria-label={isResolving ? "Resolving" : data.status === "completed" ? "Resolved" : "Resolve Call"}
      >
        <PhoneOff />
      </button>
    </div>
  );
};

export default CallDetails;
