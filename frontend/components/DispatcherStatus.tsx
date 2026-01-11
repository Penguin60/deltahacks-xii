import React from "react";
import { Dispatcher } from "@/hooks/useDispatchers";

interface DispatcherStatusProps {
  dispatchers: Dispatcher[];
}

const DispatcherStatus: React.FC<DispatcherStatusProps> = ({ dispatchers }) => {
  return (
    <div className="p-4 bg-zinc-800 rounded-lg h-full overflow-y-auto w-full">
      <h2 className="text-white font-bold text-xl mb-4">Dispatcher Status</h2>
      <div className="space-y-3">
        {dispatchers.map((dispatcher) => {
          const timeRemaining = dispatcher.endTime
            ? Math.max(0, Math.ceil((dispatcher.endTime - Date.now()) / 1000))
            : null;

          return (
            <div
              key={dispatcher.id}
              className={`p-3 rounded-md flex justify-between items-center ${
                dispatcher.status === "busy" ? "bg-blue-700" : "bg-zinc-700"
              }`}
            >
              <span className="text-white font-medium">
                Dispatcher {dispatcher.id}:
              </span>
              {dispatcher.status === "busy" ? (
                <div className="flex flex-col items-end">
                  <span className="text-blue-200 text-sm">
                    {dispatcher.isInitialBusy
                      ? "Initial Call (Local)"
                      : `Call ${dispatcher.callId?.substring(0, 8)}...`}
                  </span>
                  {timeRemaining !== null && (
                    <span className="text-blue-300 text-xs">
                      {Math.floor(timeRemaining / 60)}:
                      {String(timeRemaining % 60).padStart(2, "0")} remaining
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-zinc-300 text-sm">Idle</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DispatcherStatus;
