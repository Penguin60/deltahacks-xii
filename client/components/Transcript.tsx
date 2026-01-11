import TranscriptionLine from "./generic/TranscriptionLine";

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
}
