"use client"

import { PhoneOff } from "lucide-react";

export default function ActiveCall({ data, hangUpHandler }: { data: any; hangUpHandler: () => void }) {
  if (!data) return (<div></div>);
  return (
    <div className="flex flex-col items-center justify-start w-full h-full py-12 text-white bg-zinc-800">
      <div className="text-5xl font-extrabold tracking-tight">{data.result.phone}</div>
      <div className="mt-1 text-lg font-semibold text-zinc-300">{data.result.location}</div>

      <div className="mt-3 flex gap-2">
        <span className="px-3 py-1 rounded-full bg-zinc-700 text-sm text-zinc-200">
          {data.result.startedAgo}
        </span>
      </div>

      <p className="mt-5 max-w-3xl text-center text-base leading-relaxed text-zinc-100 px-4">
        {data.result.desc}
      </p>

      <button
        onClick={hangUpHandler}
        className="mt-8 w-14 h-14 rounded-full bg-red-700 hover:bg-red-800 flex items-center justify-center shadow-lg transition-colors"
        aria-label="Hang up"
      >
        <PhoneOff />
      </button>
    </div>
  );
}