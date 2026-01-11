# `old-logic/` snapshot (copied from current frontend)

This folder is a **copy** of the frontend files involved in:

- Config page logic (writes `simulationConfig` to `localStorage`)
- Dashboard queue polling (`GET /queue`)
- Auto-dispatcher claiming + manual resolving (both call `DELETE /remove/:id`)

## Included files

### Config page
- `app/config/page.tsx`
- `components/ui/button.tsx`
- `components/ui/input.tsx`
- `components/ui/select.tsx`

### Dashboard queue polling + selection
- `app/dashboard/page.tsx`
- `providers/QueryProvider.tsx`
- `app/layout.tsx`
- `components/Queue.tsx`
- `components/generic/QueuedCall.tsx`
- `components/generic/QueuedCallSkeleton.tsx`

### Remove requests + call details
- `hooks/useDispatchers.ts` (auto-claim calls via `DELETE /remove/:id`)
- `components/CallDetails.tsx` (Resolve button triggers `onResolve` from dashboard)
- `components/Transcript.tsx`
- `components/generic/TranscriptionLine.tsx`
- `components/DispatcherStatus.tsx`

