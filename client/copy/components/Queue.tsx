"use client";

import QueuedCall from "./generic/QueuedCall";
import QueuedCallSkeleton from "./generic/QueuedCallSkeleton";

// Define props for Queue component
interface QueueProps {
    data: any[] | undefined;
    isPending: boolean;
    error: Error | null;
    onSelectCall: (id: string) => void;
    selectedCallId: string | null;
}


export default function Queue({ data, isPending, error, onSelectCall, selectedCallId }: QueueProps) {

	if (isPending && !data) {
        return (
            <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                    <QueuedCallSkeleton key={i} />
                ))}
            </div>
        );
    }

	if (error) return <div>An error has occurred: {error.message}</div>;
	
    if (!data || data.length === 0) return <div>No calls in queue.</div>;

	return (
		<div className="space-y-2">
			{data.map((call: any) => (
				<QueuedCall
					key={call.id}
					id={call.id} // Pass the id to QueuedCall
					type={call.incidentType}
					location={call.location}
					time={call.time}
					severity={Number(call.severity_level) || 1}
					suggestedAction={call.suggested_actions}
					callers={1}
                    onSelectCall={onSelectCall} // Pass onSelectCall
                    isSelected={call.id === selectedCallId} // Pass isSelected
				/>
			))}
		</div>
	);
}

