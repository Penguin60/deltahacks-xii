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
    <div>
      {transcript.map((transcriptline, index) => (
        <TranscriptionLine
          key={index} // Use index as key if no unique id is available for transcript lines
          text={transcriptline.text}
          speaker="CALLER"
          time={transcriptline.time}
        />
      ))}
    </div>
  );
}

