"use client";

<<<<<<< HEAD
import ActiveCall from "@/components/ActiveCall";
import Queue from "@/components/Queue";
import Transcript from "@/components/Transcript";
import { useState } from "react";

export default function Home() {
  const [activeCall, setActiveCall] = useState("");
  const [data, setData] = useState<any>();
  const today = new Date().toISOString().split("T")[0];

  const handleCallSelect = (callId: string) => {
    setActiveCall(callId);
    console.log(callId);
    fetch(`http://localhost:8000/agent/${callId}`, { cache: "no-store" })
      .then(async (res) => {
        if (!res.ok) throw new Error("Agent not found");
        return res.json();
      })
      .then((json) => {
        console.log(json);
        setData(json);
      })
      .catch((e) => console.log(e.message));
    fetch(`http://localhost:8000/remove/${callId}`, {
      method: "DELETE",
    }).then(async (res) => {
      if (!res.ok) throw new Error("Agent not found");
      return res.json();
    });
  };

	return (
		<div className="flex flex-col min-h-screen font-sans bg-zinc-900 p-5 flex-col">
			<div className="flex flex-row w-full h-12 bg-zinc-800 p-3 items-center justify-between">
                <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
                <h1 className="text-white font-normal text-md">{today}</h1>
            </div>
            <div className="flex flex-row flex-1 w-full mt-3">
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[1.5] p-4">
                  <Queue onCallSelect={handleCallSelect} />
                </div>
                <div className="flex flex-col flex-1 flex-[4] mx-3">
                    <div className="flex flex-1 bg-zinc-800">
                      <ActiveCall hangUpHandler={() => {setData("")}} data={data} />
                    </div>
                </div>
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[2] p-4">
                    <h1 className="text-white font-bold text-xl">Transcript</h1>
                    <Transcript data={data} />
                </div>
            </div>
		</div>
	);
=======
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
              className="w-full h-12 text-lg border-zinc-600 hover:bg-zinc-700 text-white"
            >
              Configure Centre Settings
            </Button>
          </Link>
        </div>

        <p className="text-zinc-500 text-sm pt-8">
          Simulate incoming 911 calls with intelligent queue prioritization.
        </p>
      </div>
    </div>
  );
>>>>>>> cd8db18 (checkpoint: initial client polling logic)
}
