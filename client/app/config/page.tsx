"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Link from "next/link";
import { generateUlid, getIdSuffix } from "@/lib/ulid";

// TranscriptIn shape for /invoke
interface TranscriptIn {
  text: string;
  time: string;
  location: string;
  duration: string;
}

// Custom call with client ID for tracking
interface CustomCall {
  clientId: string;
  transcript: TranscriptIn;
}

export default function ConfigPage() {
  const router = useRouter();
  
  // Basic config
  const [numDispatchers, setNumDispatchers] = useState("5");
  const [numIncomingCalls, setNumIncomingCalls] = useState("10");
  const [callHandleTime, setCallHandleTime] = useState("3");
  const [initialBusyDispatchers, setInitialBusyDispatchers] = useState("0");
  const [initialBusyHandleTime, setInitialBusyHandleTime] = useState("1");

  // Custom calls
  const [customIncomingCalls, setCustomIncomingCalls] = useState<CustomCall[]>([]);
  const [customCurrentCalls, setCustomCurrentCalls] = useState<CustomCall[]>([]);

  // New call form state
  const [newCallType, setNewCallType] = useState<"incoming" | "current">("incoming");
  const [newCallText, setNewCallText] = useState("");
  const [newCallTime, setNewCallTime] = useState("2026-01-10T12:00:00Z");
  const [newCallLocation, setNewCallLocation] = useState("M5H2N2");
  const [newCallDuration, setNewCallDuration] = useState("01:30");

  const handleAddCustomCall = () => {
    if (!newCallText.trim()) {
      alert("Please enter call text/transcript.");
      return;
    }

    const newCall: CustomCall = {
      clientId: generateUlid(),
      transcript: {
        text: newCallText.trim(),
        time: newCallTime,
        location: newCallLocation,
        duration: newCallDuration,
      },
    };

    if (newCallType === "incoming") {
      setCustomIncomingCalls((prev) => [...prev, newCall]);
    } else {
      setCustomCurrentCalls((prev) => [...prev, newCall]);
    }

    // Reset form
    setNewCallText("");
  };

  const handleRemoveIncomingCall = (clientId: string) => {
    setCustomIncomingCalls((prev) => prev.filter((c) => c.clientId !== clientId));
  };

  const handleRemoveCurrentCall = (clientId: string) => {
    setCustomCurrentCalls((prev) => prev.filter((c) => c.clientId !== clientId));
  };

  const handleStartSimulation = () => {
    const config = {
      dispatchers: parseInt(numDispatchers, 10) || 5,
      incomingCalls: parseInt(numIncomingCalls, 10) || 10,
      handleTime: callHandleTime,
      initialBusyDispatchers: parseInt(initialBusyDispatchers, 10) || 0,
      initialBusyHandleTime: initialBusyHandleTime,
      // Custom calls override defaults if present
      customIncomingCalls: customIncomingCalls,
      customCurrentCalls: customCurrentCalls,
    };
    localStorage.setItem("simulationConfig", JSON.stringify(config));
    router.push("/dashboard");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-900 text-white py-8">
      <div className="w-full max-w-2xl p-8 space-y-8 bg-zinc-800 rounded-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold">Configure Simulation</h1>
          <p className="text-zinc-400">Set the parameters for the call center.</p>
        </div>

        <div className="space-y-4">
          {/* Number of Dispatchers */}
          <div>
            <label
              htmlFor="dispatchers"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Number of Dispatchers
            </label>
            <Input
              id="dispatchers"
              type="number"
              min="1"
              value={numDispatchers}
              onChange={(e) => setNumDispatchers(e.target.value)}
              className="bg-zinc-700 border-zinc-600 text-white"
            />
          </div>

          {/* Initial Incoming Calls (default count) */}
          <div>
            <label
              htmlFor="incoming-calls"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Default Incoming Calls (Queue)
            </label>
            <Input
              id="incoming-calls"
              type="number"
              min="0"
              value={numIncomingCalls}
              onChange={(e) => setNumIncomingCalls(e.target.value)}
              className="bg-zinc-700 border-zinc-600 text-white"
            />
            <p className="text-zinc-500 text-xs mt-1">
              Used if no custom incoming calls are added below.
            </p>
          </div>

          {/* Call Handle Time (for dispatchers picking from queue) */}
          <div>
            <label
              htmlFor="handle-time"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Call Handle Time (Queue Calls)
            </label>
            <Select onValueChange={setCallHandleTime} defaultValue={callHandleTime}>
              <SelectTrigger
                id="handle-time"
                className="bg-zinc-700 border-zinc-600 text-white w-full"
              >
                <SelectValue placeholder="Select a duration" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-700 border-zinc-600">
                <SelectItem value="1">1 Minute</SelectItem>
                <SelectItem value="3">3 Minutes</SelectItem>
                <SelectItem value="5">5 Minutes</SelectItem>
                <SelectItem value="random">Random (1, 3, or 5)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <hr className="border-zinc-600 my-4" />

          {/* Initial Busy Dispatchers (Current Calls - default count) */}
          <div>
            <label
              htmlFor="initial-busy"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Default Initial Busy Dispatchers (Current Calls)
            </label>
            <Input
              id="initial-busy"
              type="number"
              min="0"
              value={initialBusyDispatchers}
              onChange={(e) => setInitialBusyDispatchers(e.target.value)}
              className="bg-zinc-700 border-zinc-600 text-white"
            />
            <p className="text-zinc-500 text-xs mt-1">
              Used if no custom current calls are added below.
            </p>
          </div>

          {/* Initial Busy Handle Time */}
          <div>
            <label
              htmlFor="initial-busy-time"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Current Call Handle Time
            </label>
            <Select
              onValueChange={setInitialBusyHandleTime}
              defaultValue={initialBusyHandleTime}
            >
              <SelectTrigger
                id="initial-busy-time"
                className="bg-zinc-700 border-zinc-600 text-white w-full"
              >
                <SelectValue placeholder="Select a duration" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-700 border-zinc-600">
                <SelectItem value="1">1 Minute</SelectItem>
                <SelectItem value="3">3 Minutes</SelectItem>
                <SelectItem value="5">5 Minutes</SelectItem>
                <SelectItem value="random">Random (1, 3, or 5)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <hr className="border-zinc-600 my-4" />

          {/* Custom Calls Section */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-white">Custom Calls</h2>
            <p className="text-zinc-400 text-sm">
              Add custom calls to override defaults. Custom calls will be used instead of random mock data.
            </p>

            {/* Add new call form */}
            <div className="bg-zinc-700 p-4 rounded-md space-y-3">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Call Type
                </label>
                <Select
                  onValueChange={(val) => setNewCallType(val as "incoming" | "current")}
                  defaultValue={newCallType}
                >
                  <SelectTrigger className="bg-zinc-600 border-zinc-500 text-white w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-700 border-zinc-600">
                    <SelectItem value="incoming">Incoming (Queue)</SelectItem>
                    <SelectItem value="current">Current (Client-only)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Transcript Text
                </label>
                <textarea
                  value={newCallText}
                  onChange={(e) => setNewCallText(e.target.value)}
                  className="w-full bg-zinc-600 border-zinc-500 text-white rounded-md p-2 text-sm min-h-[80px]"
                  placeholder="e.g. There's a fire at 123 Main Street..."
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Time (ISO)
                  </label>
                  <Input
                    value={newCallTime}
                    onChange={(e) => setNewCallTime(e.target.value)}
                    className="bg-zinc-600 border-zinc-500 text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Location
                  </label>
                  <Input
                    value={newCallLocation}
                    onChange={(e) => setNewCallLocation(e.target.value)}
                    className="bg-zinc-600 border-zinc-500 text-white text-xs"
                    placeholder="M5H2N2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Duration
                  </label>
                  <Input
                    value={newCallDuration}
                    onChange={(e) => setNewCallDuration(e.target.value)}
                    className="bg-zinc-600 border-zinc-500 text-white text-xs"
                    placeholder="01:30"
                  />
                </div>
              </div>

              <Button
                onClick={handleAddCustomCall}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                Add Call
              </Button>
            </div>

            {/* Custom Incoming Calls List */}
            {customIncomingCalls.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-zinc-300">
                  Custom Incoming Calls ({customIncomingCalls.length})
                </h3>
                {customIncomingCalls.map((call) => (
                  <div
                    key={call.clientId}
                    className="flex items-center justify-between bg-zinc-700 p-2 rounded-md"
                  >
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-blue-400 font-mono">
                        [{getIdSuffix(call.clientId)}]
                      </span>
                      <p className="text-sm text-white truncate">
                        {call.transcript.text.substring(0, 60)}...
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveIncomingCall(call.clientId)}
                      className="text-red-400 hover:text-red-300 hover:bg-zinc-600"
                    >
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* Custom Current Calls List */}
            {customCurrentCalls.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-zinc-300">
                  Custom Current Calls ({customCurrentCalls.length})
                </h3>
                {customCurrentCalls.map((call) => (
                  <div
                    key={call.clientId}
                    className="flex items-center justify-between bg-zinc-700 p-2 rounded-md"
                  >
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-orange-400 font-mono">
                        [{getIdSuffix(call.clientId)}]
                      </span>
                      <p className="text-sm text-white truncate">
                        {call.transcript.text.substring(0, 60)}...
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveCurrentCall(call.clientId)}
                      className="text-red-400 hover:text-red-300 hover:bg-zinc-600"
                    >
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col space-y-4">
          <Button
            onClick={handleStartSimulation}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            Start Simulation
          </Button>
          <Link href="/" passHref>
            <Button
              variant="outline"
              className="w-full border-zinc-600 hover:bg-zinc-700 text-white"
            >
              Back to Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
