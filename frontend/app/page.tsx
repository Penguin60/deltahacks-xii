"use client";

import ActiveCall from "@/components/ActiveCall";
import Queue from "@/components/Queue";
import Transcript from "@/components/Transcript";
import { useState } from "react";

export default function Home() {
  const [activeCall, setActiveCall] = useState("");
  const [data, setData] = useState<any>();

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
      <div className="flex flex-row w-full h-12 bg-zinc-800 p-3 items-center">
        <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
      </div>
      <div className="flex flex-row flex-1 w-full mt-3">
        <div className="flex flex-col flex-1 bg-zinc-800 flex-[1.5] p-4">
          <h1 className="text-white font-bold text-xl">Queue</h1>
          <Queue onCallSelect={handleCallSelect} />
        </div>
        <div className="flex flex-col flex-1 flex-[4] mx-3">
          <div className="flex flex-1 bg-zinc-800">
            <ActiveCall
              hangUpHandler={() => {
                setData("");
              }}
              data={data}
            />
          </div>
        </div>
        <div className="flex flex-col flex-1 bg-zinc-800 flex-[2] p-4">
          <h1 className="text-white font-bold text-xl">Transcript</h1>
          <Transcript data={data} />
        </div>
      </div>
    </div>
  );
}
