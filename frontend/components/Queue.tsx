"use client";

import {
	QueryClient,
	QueryClientProvider,
	useQuery,
} from "@tanstack/react-query";
import QueuedCall from "./generic/QueuedCall";

const queryClient = new QueryClient();

function QueueContent() {
	const { isPending, error, data } = useQuery({
		queryKey: ["repoData"],
		queryFn: () =>
			fetch("http://localhost:8000/queue").then((res) => res.json()),
		refetchInterval: 500,
		staleTime: 0,
		placeholderData: (previousData) => previousData,
		refetchIntervalInBackground: false,
	});

	if (isPending) return <div>Loading...</div>;

	if (error) return <div>An error has occurred: {error.message}</div>;

	return (
		<div>
			{data.map((call: any) => (
				<QueuedCall
					key={call.id}
					type={call.incidentType}
					location={call.location}
					time={call.time}
					severity={call.severity_level}
					callers={1}
				/>
			))}
		</div>
	);
}

export default function Queue() {
	return (
		<QueryClientProvider client={queryClient}>
			<QueueContent />
		</QueryClientProvider>
	);
}
