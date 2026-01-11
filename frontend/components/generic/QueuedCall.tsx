export default function QueuedCall({
  type,
  location,
  time,
  severity,
  callers,
}: {
  type: string;
  location: string;
  time: string;
  severity: number;
  callers: number;
}) {
  return (
    <div className="w-full flex justify-between items-center py-4">
      <div>
        <h1 className="text-white text-2xl font-semibold mb-2 leading-none">{type}</h1>
        <div className="bg-zinc-400 w-fit px-2 rounded-full text-sm">
          <h3 className="text-white text-sm">{callers} Callers</h3>
        </div>
      </div>
      <div className="flex flex-col items-end justify-center">
        <div
          className={`w-3 h-3 rounded-full ${
            severity === 3
              ? "bg-red-800"
              : severity === 2
              ? "bg-orange-500"
              : "bg-green-700"
          }`}
        />
        <h3 className="text-zinc-400 text-sm leading-tight">{time}</h3>
        <h3 className="text-zinc-400 text-sm leading-tight">{location}</h3>
      </div>
    </div>
  );
}
