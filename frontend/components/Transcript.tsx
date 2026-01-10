import TranscriptionLine from "./generic/TranscriptionLine";

export default async function Transcript(id: string) {
  let response = await fetch(`http://localhost:8000/call/${id}`, {
    cache: "no-store",
  });
  let data = await response.json();
  return (
    <div>
      {data?.transcript.map((transcriptline: any) => (
        <TranscriptionLine
          text={transcriptline.text}
          speaker="CALLER"
          time={transcriptline.time}
        />
      ))}
    </div>
  );
}
