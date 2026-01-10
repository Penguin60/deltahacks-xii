import Queue from "@/components/Queue";

export default function Home() {
	return (
		<div className="flex flex-col min-h-screen font-sans bg-zinc-900 p-5 flex-col">
			<div className="flex flex-row w-full h-12 bg-zinc-800 p-3 items-center">
                <h1 className="text-white font-bold text-xl">Delta Dispatch</h1>
            </div>
            <div className="flex flex-row flex-1 w-full mt-3">
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[1.5] p-3">
                  <h1 className="text-white font-bold text-xl">Queue</h1>
                  <Queue />
                </div>
                <div className="flex flex-col flex-1 flex-[4] mx-3">
                    <div className="flex flex-[5] bg-zinc-800 mb-3">
                      
                    </div>
                    <div className="flex flex-[2.5] bg-zinc-800">

                    </div>
                </div>
                <div className="flex flex-col flex-1 bg-zinc-800 flex-[2] p-3">
                    <h1 className="text-white font-bold text-xl">Transcript</h1>
                </div>
            </div>
		</div>
	);
}