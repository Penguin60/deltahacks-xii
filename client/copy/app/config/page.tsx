"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import Link from 'next/link';

export default function ConfigPage() {
  const router = useRouter();
  const [numDispatchers, setNumDispatchers] = useState('5');
  const [numIncomingCalls, setNumIncomingCalls] = useState('10');
  const [callHandleTime, setCallHandleTime] = useState('3');

  const handleStartSimulation = () => {
    const config = {
      dispatchers: parseInt(numDispatchers, 10) || 5,
      incomingCalls: parseInt(numIncomingCalls, 10) || 10,
      handleTime: callHandleTime,
    };
    localStorage.setItem('simulationConfig', JSON.stringify(config));
    router.push('/dashboard');
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-900 text-white">
      <div className="w-full max-w-md p-8 space-y-8 bg-zinc-800 rounded-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold">Configure Simulation</h1>
          <p className="text-zinc-400">Set the parameters for the call center.</p>
        </div>
        <div className="space-y-4">
          <div>
            <label htmlFor="dispatchers" className="block text-sm font-medium text-zinc-300 mb-2">
              Number of Dispatchers
            </label>
            <Input
              id="dispatchers"
              type="number"
              value={numDispatchers}
              onChange={(e) => setNumDispatchers(e.target.value)}
              className="bg-zinc-700 border-zinc-600"
            />
          </div>
          <div>
            <label htmlFor="incoming-calls" className="block text-sm font-medium text-zinc-300 mb-2">
              Initial Incoming Calls
            </label>
            <Input
              id="incoming-calls"
              type="number"
              value={numIncomingCalls}
              onChange={(e) => setNumIncomingCalls(e.target.value)}
              className="bg-zinc-700 border-zinc-600"
            />
          </div>
          <div>
            <label htmlFor="handle-time" className="block text-sm font-medium text-zinc-300 mb-2">
              Call Handle Time
            </label>
            <Select onValueChange={setCallHandleTime} defaultValue={callHandleTime}>
              <SelectTrigger id="handle-time" className="bg-zinc-700 border-zinc-600">
                <SelectValue placeholder="Select a duration" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 Minute</SelectItem>
                <SelectItem value="3">3 Minutes</SelectItem>
                <SelectItem value="5">5 Minutes</SelectItem>
                <SelectItem value="random">Random (1, 3, or 5)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col space-y-4">
            <Button onClick={handleStartSimulation} className="w-full bg-blue-600 hover:bg-blue-700">
                Start Simulation
            </Button>
            <Link href="/" passHref>
                <Button variant="outline" className="w-full border-zinc-600 hover:bg-zinc-700">
                    Back to Home
                </Button>
            </Link>
        </div>
      </div>
    </div>
  );
}

