"use client";

import QueuedCall from "./generic/QueuedCall";
import QueuedCallSkeleton from "./generic/QueuedCallSkeleton";
import { QueueItem } from "@/lib/api";

<<<<<<< HEAD
const queryClient = new QueryClient();

type QueueProps = {
    onCallSelect: (call: any) => void;
};


function QueueContent({ onCallSelect }: QueueProps) {
	const { isPending, error, data } = useQuery({
		queryKey: ["repoData"],
		queryFn: () =>
			fetch("http://localhost:8000/queue").then((res) => res.json()),
		refetchInterval: 500,
		staleTime: 0,
		placeholderData: (previousData) => previousData,
		refetchIntervalInBackground: false,
	});

    const sortedData = useMemo(() => {
        if (!Array.isArray(data)) return [];
        return [...data].sort((a, b) => Number(b.severity_level) - Number(a.severity_level))
    }, [data])

	if (isPending) return <div>Loading...</div>;

	if (error) return <div>An error has occurred: {error.message}</div>;
	console.log("[Queue] fetched queue data", data);

	return (
		<div className="overflow-y-auto">
			{sortedData.map((call: any) => (
				<QueuedCall
					key={call.id}
                    id={call.id}
					type={call.incidentType}
					location={call.location}
					time={call.time}
					severity={Number(call.severity_level) || 1}
					suggestedAction={call.suggested_actions}
					callers={1}
                    onCallSelect={onCallSelect}
				/>
			))}
		</div>
	);
=======
interface QueueProps {
  data: QueueItem[] | undefined;
  isPending: boolean;
  error: Error | null;
  onSelectCall: (id: string) => void;
  selectedCallId: string | null;
>>>>>>> cd8db18 (checkpoint: initial client polling logic)
}

export default function Queue({
  data,
  isPending,
  error,
  onSelectCall,
  selectedCallId,
}: QueueProps) {
  if (isPending && !data) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <QueuedCallSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) return <div className="text-red-400">An error has occurred: {error.message}</div>;

  if (!data || data.length === 0) {
    return <div className="text-zinc-400">No calls in queue.</div>;
  }

  return (
    <div className="space-y-2">
      {data.map((call) => (
        <QueuedCall
          key={call.id}
          id={call.id}
          type={call.incidentType}
          location={call.location}
          time={call.time}
          severity={Number(call.severity_level) || 1}
          suggestedAction={call.suggested_actions}
          callers={1}
          onSelectCall={onSelectCall}
          isSelected={call.id === selectedCallId}
        />
      ))}
    </div>
  );
}
