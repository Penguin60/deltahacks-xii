"use client";

import { useEffect, useState } from "react";
import TranscriptionLine from "./generic/TranscriptionLine";

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
}
