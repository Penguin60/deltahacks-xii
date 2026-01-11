"use client";

import {
	QueryClient,
	QueryClientProvider,
	useQuery,
} from "@tanstack/react-query";
import QueuedCall from "./generic/QueuedCall";
import { useMemo } from "react";

const queryClient = new QueryClient();

type QueueProps = {
    onCallSelect?: (call: any) => void;
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
		<div>
			{sortedData.map((call: any) => (
				<QueuedCall
					key={call.id}
					type={call.incidentType}
					location={call.location}
					time={call.time}
					severity={Number(call.severity_level) || 1}
					suggestedAction={call.suggested_actions}
					callers={1}
				/>
			))}
		</div>
	);
}

export default function Queue({ onCallSelect }: QueueProps) {
	return (
		<QueryClientProvider client={queryClient}>
			<QueueContent onCallSelect={onCallSelect} />
		</QueryClientProvider>
	);
}
