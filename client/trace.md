> trace phase 1 UI:

# Files Created/Modified
Foundational
- frontend/providers/QueryProvider.tsx - TanStack Query provider with retry/delay config
- frontend/lib/api.ts - Centralized API helpers with NEXT_PUBLIC_API_BASE_URL support
- frontend/lib/mock-data.ts - Mock transcripts for simulation initialization
- frontend/app/layout.tsx - Updated to wrap app with QueryProvider

# UI Components 
- frontend/components/ui/button.tsx - shadcn Button component
- frontend/components/ui/input.tsx - shadcn Input component
- frontend/components/ui/select.tsx - shadcn Select component

# Pages
- frontend/app/page.tsx - Landing page with "Start with Defaults" and "Configure" buttons
- frontend/app/config/page.tsx - Config page with dispatchers, incoming calls, handle time, initial busy dispatchers settings
- frontend/app/dashboard/page.tsx - Main dashboard with safe polling, session guard for init, and live queue updates

# Components
frontend/components/Queue.tsx - Refactored to accept data externally
frontend/components/generic/QueuedCall.tsx - Updated with selection support
frontend/components/generic/QueuedCallSkeleton.tsx - Loading skeleton
frontend/components/DispatcherStatus.tsx - Shows dispatcher status with countdown timers
frontend/components/CallDetails.tsx - Call details panel with resolve button
frontend/components/Transcript.tsx - Transcript display component

# Hooks
frontend/hooks/useDispatchers.ts - Dispatcher simulation with:
Initial busy dispatchers (client-only placeholders)
Per-dispatcher pickup from queue
claimedQueueIds to prevent user/dispatcher conflicts
Idempotency guards (removedIdsRef, removeInFlightRef)
DELETE /remove/{id} only called on timer completion

# Key Behaviors Implemented

- Safe Polling: Queue polls every 1s, pauses when tab hidden, uses abort signal
- Session Guard: POST /invoke initialization only runs once per session per config
- Idempotent Removes: Both user-resolve and dispatcher-complete use shared guards to ensure exactly-one - DELETE /remove/{id}
- Claimed IDs Filter: When a dispatcher claims a call, it's hidden from the queue UI immediately
- Initial Busy Dispatchers: Pure client-side placeholders that block pickup until timer completes
- To test, start the backend and run pnpm dev in the frontend folder.


> trace phase 2 UI

# ULID Helper (frontend/lib/ulid.ts)

- Added generateUlid() function for creating unique IDs for current calls
- Added getIdSuffix() helper to display the last 8 characters of IDs (more unique than prefix)

# Config Page (frontend/app/config/page.tsx)

- Added "Custom Calls" section with form to add calls
- Users can choose Incoming (Queue) or Current (Client-only) call type
- Each call has: text, time, location, duration (matching /invoke TranscriptIn schema)
- Custom calls get unique client-side ULIDs
- Lists display with remove buttons
- Config persists to localStorage with customIncomingCalls and customCurrentCalls arrays

# Dashboard Initialization (frontend/app/dashboard/page.tsx)

- If custom incoming calls exist, uses those instead of default mock data
- Otherwise falls back to incomingCalls count from config
- Always invokes on dashboard load (no session-based skipping)

# Dispatcher Simulation (frontend/hooks/useDispatchers.ts)

- Supports custom current calls with ULIDs
- Current calls queue with overflow: if more current calls than dispatchers, extras wait in a local queue
- Dispatchers pick from pending current calls first, blocking queue pickup until all current calls are done
- Only when no current calls remain do dispatchers start claiming from /queue
- Uses isCurrentCall flag instead of isInitialBusy

# Display ID Suffixes

- DispatcherStatus: Shows ...{last 8 chars} for both current and queue calls, with color coding (orange for current, blue for queue)
- CallDetails: Shows ...{last 8 chars} in header

# Dashboard Layout

- Header: Info summary moved to center (dispatchers | incoming | handle time | current | pending)
- Main area: 2-column layout (Queue left, CallDetails right)
- Bottom: DispatcherStatus panel (scrollable, fixed height)