# 911 Call Center Simulator: Spec-Driven Implementation Plan

This document outlines the development plan for building the frontend of the 911 Call Center Simulator. It refines the initial concepts from `implementation.md` into a concrete set of features and tasks.

## 1. Core Application Structure Refactoring

The current application structure will be modified to support a multi-page experience: a landing page, a configuration page, and the main dashboard.

-   **Task 1.1: Create New Landing Page**
    -   The content of `frontend/app/page.tsx` will be replaced with a new landing page.
    -   This page will feature two main actions:
        -   A `<Link href="/dashboard">` button for "Start with default configs".
        -   A `<Link href="/config">` button for "Configure centre settings".

-   **Task 1.2: Relocate Dashboard**
    -   Create a new directory: `frontend/app/dashboard/`.
    -   Move the original content of `frontend/app/page.tsx` into a new file at `frontend/app/dashboard/page.tsx`.
    -   Update any necessary import paths.

-   **Task 1.3: Create Configuration Page**
    -   Create a new directory: `frontend/app/config/`.
    -   Create a new file `frontend/app/config/page.tsx` to house the simulation configuration UI.

## 2. Configuration Page (`/config`)

This page will allow the user to customize the simulation parameters.

-   **Task 2.1: Build Configuration UI**
    -   Implement UI elements (using `shadcn/ui` components where possible) for setting:
        -   **Number of Dispatchers**: A number input.
        -   **Initial Incoming Calls**: A number input to determine how many mock calls are sent to the backend on startup.
        -   **Call Handle Time**: A select dropdown with options: "1 Minute", "3 Minutes", "5 Minutes", and "Random".
    -   The page will have a "Start Simulation" button.

-   **Task 2.2: Implement Configuration State Management**
    -   Use React's `useState` to manage the form inputs.
    -   On "Start Simulation" click, persist the chosen settings to the browser's `localStorage`.
    -   Redirect the user to `/dashboard`.

## 3. Mock Data for Call Simulation

To simulate new calls, we need a source of mock transcript data.

-   **Task 3.1: Create Mock Data File**
    -   Create a new file at `frontend/lib/mock-data.ts`.
    -   This file will export an array of `TranscriptIn` objects. Each object will contain `text`, `time`, `location`, and `duration`, compatible with the backend's `POST /invoke` endpoint. This data can be adapted from `backend/sample_incidents.json`.

## 4. Dashboard Page (`/dashboard`)

This is the main view of the simulator, where the queue and dispatcher activity are visualized.

-   **Task 4.1: Implement Simulation Initialization**
    -   On page load, read the configuration from `localStorage`. If no configuration is found, use sensible defaults (e.g., 5 dispatchers, 10 initial calls, 3-minute handle time).
    -   Trigger a one-time effect that:
        -   Selects a number of mock transcripts from `frontend/lib/mock-data.ts` based on the configuration.
        -   For each selected transcript, sends a request to the `POST /invoke` endpoint to populate the queue on the backend.

-   **Task 4.2: Develop Dispatcher Simulation Logic**
    -   Create a custom hook, `useDispatchers(queue, config)`, that encapsulates the dispatcher simulation.
    -   This hook will manage a pool of dispatcher objects (e.g., `{ id: 1, status: 'idle' | 'busy', callId: null }`).
    -   It will use a `setInterval` loop to check for idle dispatchers.
    -   When an idle dispatcher is found and the `queue` is not empty, the hook will:
        1.  Take the highest-priority call from the `queue` that is not currently selected in the UI.
        2.  Immediately call `DELETE /remove/{id}` to "claim" the call.
        3.  Update the dispatcher's state to `busy` with the `callId`.
        4.  Start a client-side timer for the configured duration.
        5.  When the timer expires, reset the dispatcher's state to `idle`.

-   **Task 4.3: Visualize Dispatcher Status**
    -   Create a `DispatcherStatus` component that receives the state from the `useDispatchers` hook and renders the current status of each dispatcher (e.g., "Dispatcher 1: Handling call 01H8XG...")

## 5. Interactive Call Details and Manual Resolution

This section covers the functionality for a user to inspect and manually resolve calls from the queue.

-   **Task 5.1: Refactor Transcript Component**
    -   Modify the existing `Transcript.tsx` component to be a presentational component that accepts transcript data as a prop, instead of fetching it internally.

-   **Task 5.2: Implement Call Details View**
    -   Create a `CallDetails` component.
    -   On the dashboard page, when a user clicks a `QueuedCall` item, its ID will be stored in the page state.
    -   The `CallDetails` component will be rendered and passed this ID.
    -   Inside `CallDetails`, use TanStack Query and the `GET /agent/{id}` endpoint to fetch the full incident details.
    -   Display the incident information (type, location, description, etc.).
    -   Render the refactored `Transcript` component with the `transcript` data from the fetched incident.

-   **Task 5.3: Add Manual Resolution**
    -   Include a "Resolve Call" button within the `CallDetails` component.
    -   When clicked, this button will trigger a request to `DELETE /remove/{id}` for the currently selected call.
    -   This will cause TanStack Query to refetch the main queue, automatically updating the UI.

-   **Task 5.4: Prevent Dispatcher Conflicts**
    -   The `useDispatchers` hook must be modified to ensure it does not select a call that is currently selected by the user in the UI. The ID of the user-selected call should be passed to the hook and excluded from the pool of available calls for dispatchers to pick up.

