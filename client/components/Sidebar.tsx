"use client";

import React, { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchIncidentDetails } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { getIdSuffix } from "@/lib/ulid";

// Suggested action types from backend schemas
const SUGGESTED_ACTIONS = [
  { value: "console", label: "Console" },
  { value: "ask for more details", label: "Ask for more details" },
  { value: "dispatch officer", label: "Dispatch officer" },
  { value: "dispatch first-aiders", label: "Dispatch first-aiders" },
  { value: "dispatch firefighters", label: "Dispatch firefighters" },
] as const;

export interface LogEntry {
  id: string;
  timestamp: Date;
  message: string;
}

interface SidebarProps {
  incidentId: string | null;
  onResolve: (id: string) => void;
  isResolving?: boolean;
  onActionClick: (action: string) => void;
  logs: LogEntry[];
}

type TabType = "details" | "transcript" | "logs";

const Sidebar: React.FC<SidebarProps> = ({
  incidentId,
  onResolve,
  isResolving = false,
  onActionClick,
  logs,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("details");
  const logsEndRef = useRef<HTMLDivElement>(null);

  const { data, isPending, error } = useQuery({
    queryKey: ["incidentDetails", incidentId],
    queryFn: async () => {
      if (!incidentId) {
        throw new Error("No incident ID provided.");
      }
      return fetchIncidentDetails(incidentId);
    },
    enabled: !!incidentId,
    staleTime: Infinity,
  });

  // Auto-scroll logs to bottom on new entries
  useEffect(() => {
    // #region agent log (debug instrumentation)
    fetch('http://127.0.0.1:7245/ingest/58ca92ad-3e00-4a67-a919-a612c94c967e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'G',location:'client/components/Sidebar.tsx:logsEffect',message:'Sidebar logs effect fired',data:{activeTab,logsLen:logs.length,incidentIdSuffix:incidentId?incidentId.slice(-8):null},timestamp:Date.now()})}).catch(()=>{});
    // #endregion agent log
    if (activeTab === "logs" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, activeTab]);

  const renderTabs = () => (
    <div className="flex border-b border-zinc-700 mb-4">
      <button
        onClick={() => setActiveTab("details")}
        className={`flex-1 py-2 text-sm font-medium transition-colors ${
          activeTab === "details"
            ? "text-white border-b-2 border-blue-500"
            : "text-zinc-400 hover:text-zinc-200"
        }`}
      >
        Details
      </button>
      <button
        onClick={() => setActiveTab("transcript")}
        className={`flex-1 py-2 text-sm font-medium transition-colors ${
          activeTab === "transcript"
            ? "text-white border-b-2 border-blue-500"
            : "text-zinc-400 hover:text-zinc-200"
        }`}
      >
        Transcript
      </button>
      <button
        onClick={() => setActiveTab("logs")}
        className={`flex-1 py-2 text-sm font-medium transition-colors ${
          activeTab === "logs"
            ? "text-white border-b-2 border-blue-500"
            : "text-zinc-400 hover:text-zinc-200"
        }`}
      >
        Logs
      </button>
    </div>
  );

  const renderTranscriptTab = () => {
    if (!incidentId) {
      return (
        <div className="flex items-center justify-center h-full text-zinc-400 text-center">
          Click on a queue entry to see transcript
        </div>
      );
    }

    if (isPending) {
      return (
        <div className="flex items-center justify-center h-full text-white">
          Loading transcript...
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-red-400 p-4">
          Error: {error.message}
        </div>
      );
    }

    if (!data || !data.transcript || data.transcript.length === 0) {
      return (
        <div className="flex items-center justify-center h-full text-zinc-400 text-center">
          No transcript available for this call.
        </div>
      );
    }

    return (
      <div className="flex flex-col h-full overflow-hidden">
        <h3 className="text-white font-semibold text-lg mb-2 flex-shrink-0">
          Call Transcript
        </h3>
        <div className="flex-1 overflow-y-auto bg-zinc-900 rounded-md">
          {data.transcript.map((entry, index) => (
            <div
              key={index}
              className="w-full flex justify-between items-start p-4 border-b border-zinc-800 last:border-b-0"
            >
              <div className="flex-1 pr-4">
                <p className="text-white text-base">{entry.text}</p>
                <p className="text-zinc-500 text-xs mt-1 uppercase">Caller</p>
              </div>
              <div className="flex-shrink-0 bg-zinc-600 px-3 py-1 rounded-full">
                <span className="text-white text-sm">{entry.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderLogsTab = () => (
    <div className="flex flex-col h-full">
      <h3 className="text-white font-semibold text-lg mb-2 flex-shrink-0">
        Dispatcher Activity Log
      </h3>
      <div className="flex-1 overflow-y-auto bg-zinc-900 rounded-md p-2 text-sm font-mono">
        {logs.length === 0 ? (
          <p className="text-zinc-500 text-center py-4">No activity yet.</p>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="text-zinc-300 py-1 border-b border-zinc-800">
              <span className="text-zinc-500">
                {log.timestamp.toLocaleTimeString()}
              </span>{" "}
              {log.message}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );

  const renderDetailsTab = () => {
    if (!incidentId) {
      return (
        <div className="flex items-center justify-center h-full text-zinc-400 text-center">
          Click on a queue entry to see details
        </div>
      );
    }

    if (isPending) {
      return (
        <div className="flex items-center justify-center h-full text-white">
          Loading call details...
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-red-400 p-4">
          Error: {error.message}
        </div>
      );
    }

    if (!data) {
      return (
        <div className="flex items-center justify-center h-full text-zinc-400">
          Incident not found.
        </div>
      );
    }

    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <h2 className="text-white font-bold text-xl mb-3">
            Call Details: ...{getIdSuffix(data.id, 8)}
          </h2>
          
          {/* Incident Details */}
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

          {/* Message / Original Call */}
          {data.message && (
            <div className="mb-4">
              <h3 className="text-white font-semibold text-lg mb-2">Original Message</h3>
              <p className="text-zinc-300 text-sm bg-zinc-900 p-2 rounded">{data.message}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mb-4">
            <h3 className="text-white font-semibold text-lg mb-2">Actions</h3>
            <div className="grid grid-cols-1 gap-2">
              {SUGGESTED_ACTIONS.map((action) => (
                <Button
                  key={action.value}
                  variant="outline"
                  size="sm"
                  onClick={() => onActionClick(action.label)}
                  className="w-full justify-start text-left"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Resolve Button - Fixed at bottom */}
        <div className="flex-shrink-0 pt-4 border-t border-zinc-700">
          <Button
            onClick={() => onResolve(data.id)}
            className="w-full bg-green-600 hover:bg-green-700"
            disabled={data.status === "completed" || isResolving}
          >
            {isResolving
              ? "Resolving..."
              : data.status === "completed"
              ? "Resolved"
              : "Resolve Call"}
          </Button>
        </div>
      </div>
    );
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "details":
        return renderDetailsTab();
      case "transcript":
        return renderTranscriptTab();
      case "logs":
        return renderLogsTab();
      default:
        return renderDetailsTab();
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-800 rounded-lg p-4">
      {renderTabs()}
      <div className="flex-1 overflow-hidden">
        {renderActiveTab()}
      </div>
    </div>
  );
};

export default Sidebar;
