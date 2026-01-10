import TranscriptionLine from "@/components/TranscriptionLine";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen font-sans bg-zinc-900">
        <h1 className="text-white">Hello world</h1>
        <div className="w-[400px] bg-black">
          <TranscriptionLine text="This is a sample transcription line." speaker="Speaker 1" time="01:23" />
        </div>
    </div>
  );
}