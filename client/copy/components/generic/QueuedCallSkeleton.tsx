// components/generic/QueuedCallSkeleton.tsx
export default function QueuedCallSkeleton() {
  return (
    <div className="w-full flex justify-between items-center py-4 px-3 rounded-md bg-zinc-700 animate-pulse">
      <div className="w-full">
        <div className="h-6 bg-zinc-600 rounded w-3/4 mb-3"></div>
        <div className="h-4 bg-zinc-600 rounded w-1/2 mb-2"></div>
        <div className="h-5 bg-zinc-500 rounded-full w-20"></div>
      </div>
      <div className="flex flex-col items-end justify-center w-1/4">
        <div className="w-3 h-3 rounded-full bg-zinc-600 mb-2"></div>
        <div className="h-4 bg-zinc-600 rounded w-full mb-1"></div>
        <div className="h-4 bg-zinc-600 rounded w-full"></div>
      </div>
    </div>
  );
}

