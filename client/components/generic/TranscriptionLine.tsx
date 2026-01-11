export default function TranscriptionLine({
  text,
  speaker,
  time,
}: {
  text: string;
  speaker: string;
  time: string;
}) {
  return (
    <div className="w-full flex justify-between items-center p-4">
      <div>
        <h1 className="text-white">{text}</h1>
        <h3 className="text-zinc-400 text-sm">{speaker}</h3>
      </div>
      <div className="bg-zinc-400 w-fit px-2 rounded-full text-sm">
        <h3 className="text-white">{time}</h3>
      </div>
    </div>
  );
}
