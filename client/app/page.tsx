"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

// Default simulation config
const DEFAULT_CONFIG = {
  dispatchers: 5,
  incomingCalls: 10,
  handleTime: "3",
  initialBusyDispatchers: 0,
  initialBusyHandleTime: "1",
};

function formatMinutes(value: string) {
  return value === "random" ? "Random (1/3/5 min)" : `${value} min`;
}

export default function Home() {
  const router = useRouter();

  const handleStartWithDefaults = () => {
    // Set default config in localStorage so dashboard has consistent behavior
    localStorage.setItem("simulationConfig", JSON.stringify(DEFAULT_CONFIG));
    router.push("/dashboard");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-900 text-white">
      <div className="w-full max-w-md p-8 space-y-8 text-center">
        <div>
          <h1 className="text-4xl font-bold mb-2">Delta Dispatch</h1>
          <p className="text-zinc-400 text-lg">911 Call Center Simulator</p>
        </div>

        <div className="space-y-4 pt-8">
          <Button
            onClick={handleStartWithDefaults}
            className="w-full h-12 text-lg bg-blue-600 hover:bg-blue-700"
          >
            Start with Default Configs
          </Button>

          <Link href="/config" passHref>
            <Button
              variant="outline"
              className="w-full h-12 text-lg border-zinc-600 hover:bg-zinc-700 text-black"
            >
              Configure Centre Settings
            </Button>
          </Link>
        </div>

        <div className="text-left bg-zinc-800/60 border border-zinc-700 rounded-lg p-4">
          <h2 className="text-white font-semibold text-lg mb-2">
            Default Config
          </h2>
          <dl className="text-sm space-y-2">
            <div className="flex justify-between gap-4">
              <dt className="text-zinc-400">Dispatchers</dt>
              <dd className="text-white font-medium">
                {DEFAULT_CONFIG.dispatchers}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-zinc-400">Initial Incoming Calls (Queue)</dt>
              <dd className="text-white font-medium">
                {DEFAULT_CONFIG.incomingCalls}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-zinc-400">Queue Call Handle Time</dt>
              <dd className="text-white font-medium">
                {formatMinutes(DEFAULT_CONFIG.handleTime)}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-zinc-400">Initial Busy Dispatchers</dt>
              <dd className="text-white font-medium">
                {DEFAULT_CONFIG.initialBusyDispatchers}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-zinc-400">Initial Busy Handle Time</dt>
              <dd className="text-white font-medium">
                {formatMinutes(DEFAULT_CONFIG.initialBusyHandleTime)}
              </dd>
            </div>
          </dl>
        </div>

        <p className="text-zinc-500 text-sm pt-8">
          Simulate incoming 911 calls with intelligent queue prioritization.
        </p>
      </div>
    </div>
  );
}
