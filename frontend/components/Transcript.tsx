"use client";

import { useEffect, useState } from "react";
import TranscriptionLine from "./generic/TranscriptionLine";

<<<<<<< HEAD
export default function Transcript({ data }: { data: any }) {
    if (!data) return (<div></div>);
	return (
		<div>
			{data?.result.transcript.map((transcriptline: any, idx: number) => (
				<TranscriptionLine
					key={idx}
					text={transcriptline.text}
					speaker="CALLER"
					time={transcriptline.time}
				/>
			))}
		</div>
	);
=======
interface TranscriptLineData {
  text: string;
  time: string;
}

interface TranscriptProps {
  transcript: TranscriptLineData[];
}

export default function Transcript({ transcript }: TranscriptProps) {
  return (
    <div className="space-y-2">
      {transcript.map((transcriptline, index) => (
        <TranscriptionLine
          key={index}
          text={transcriptline.text}
          speaker="CALLER"
          time={transcriptline.time}
        />
      ))}
    </div>
  );
>>>>>>> cd8db18 (checkpoint: initial client polling logic)
}
