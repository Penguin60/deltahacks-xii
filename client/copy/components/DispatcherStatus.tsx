import React from 'react';

// Assuming Dispatcher interface is available from useDispatchers.ts
interface Dispatcher {
    id: number;
    status: 'idle' | 'busy';
    callId: string | null;
    endTime: number | null;
}

interface DispatcherStatusProps {
    dispatchers: Dispatcher[];
}

const DispatcherStatus: React.FC<DispatcherStatusProps> = ({ dispatchers }) => {
    return (
        <div className="p-4 bg-zinc-800 rounded-lg h-full overflow-y-auto">
            <h2 className="text-white font-bold text-xl mb-4">Dispatcher Status</h2>
            <div className="space-y-3">
                {dispatchers.map((dispatcher) => (
                    <div
                        key={dispatcher.id}
                        className={`p-3 rounded-md flex justify-between items-center ${
                            dispatcher.status === 'busy' ? 'bg-blue-700' : 'bg-zinc-700'
                        }`}
                    >
                        <span className="text-white font-medium">
                            Dispatcher {dispatcher.id}:
                        </span>
                        {dispatcher.status === 'busy' ? (
                            <span className="text-blue-200 text-sm">
                                Handling Call {dispatcher.callId ? dispatcher.callId.substring(0, 8) + '...' : 'N/A'}
                            </span>
                        ) : (
                            <span className="text-zinc-300 text-sm">Idle</span>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default DispatcherStatus;

