import React, { useEffect, useState } from "react";
import { Dispatcher } from "@/hooks/useDispatchers";
import { getIdSuffix } from "@/lib/ulid";

interface DispatcherStatusProps {
  dispatchers: Dispatcher[];
}

const DispatcherStatus: React.FC<DispatcherStatusProps> = ({ dispatchers }) => {
  // Force re-render every second to update countdown timers
  const [, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

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
                dispatcher.status === "busy"
                  ? dispatcher.isCurrentCall
                    ? "bg-orange-700"
                    : "bg-blue-700"
                  : "bg-zinc-700"
              }`}
            >
              <span className="text-white font-medium">
                Dispatcher {dispatcher.id}:
              </span>
              {dispatcher.status === "busy" ? (
                <div className="flex flex-col items-end">
                  <span
                    className={`text-sm ${
                      dispatcher.isCurrentCall ? "text-orange-200" : "text-blue-200"
                    }`}
                  >
                    {dispatcher.isCurrentCall
                      ? `Current ...${getIdSuffix(dispatcher.callId || "", 8)}`
                      : `Queue ...${getIdSuffix(dispatcher.callId || "", 8)}`}
                  </span>
                  {timeRemaining !== null && (
                    <span
                      className={`text-xs ${
                        dispatcher.isCurrentCall ? "text-orange-300" : "text-blue-300"
                      }`}
                    >
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
