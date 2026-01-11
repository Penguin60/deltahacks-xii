I am trying to make a 911 call center simulator enhanced with intelligent queuing for incoming calls. However, for the setup of a proof of concept demo, it is impossible for me to have more than 1 Twilo phone call, so I need to simulate 2 types of calls to the center (the frontend UI): incoming calls, calls where a human dispatcher is not available to pick up, so the human is typically placed on "hold", and current calls, which are calls being intercepted by the dispatchers available. Since the frontend is essentially acting as the dispatch center, I want to mock data for some incoming and current calls, and I want to make this configurable on the frontend. The backend receives incoming calls, ranks them, and then stores the metadata of the in a redis Queue and sends the rest of the information to the database, which the frontend polls using Tanstack Query. 
The Query polls and returns an array of the following JSON: 
queue_entry = {
       "id": triage_incident.id,
       "incidentType": _enum_value(triage_incident.incidentType),
       "location": string,
       "Time”: string,
       "Severity_level": string,
       "Suggested_actions": string,
   }

Type checking is done on the backend. There is no need for any type checking on the frontend. 
The user can go to the config page, choose the specifications of the incoming calls, current calls, and number of dispatchers. The configuration for incoming and current calls are below:
1. Incoming (“live”) calls: by default, they are stored inside a static JSON file that corresponds to the backend API invoke's JSON in the request bodies. When the simulation is run, a POST request is sent to the backend for each incoming call present or the number of incoming calls specified by the user, which is then enqueued asynchronously and . If the user selects an element on the queue, a GET() is called to get_incidents using the ULID from the queue. 
2. Current calls: simulate calls that are currently being handled by the available dispatchers. When the simulation starts, a timeout() happens, and when the timeout is done, the current call being handled is removed from runtime memory, and the Queue’s next top element is popped and sent to this dispatcher, and disappears from the Queue. This incoming call from the queue becomes a current call, and a hard coded value for a timeout is carried out with a dispatcher being consumed by this event. After this is done, a remove() call is sent ONLY for elements in the list. 

The user logic needs to go like this:
On startup, the user is greeted with a start page with 2 buttons:
Start with default configs
Configure centre settings 
If the user clicks the default configs, this takes them to the dashboard page directly
If the user clicks on config centre settings, this takes the user to the config page, where the user can configure:
Number of current calls, and duration time (1 min, 3 min, 5 min, random 1 of 3 above options)
Number of incoming “live” calls to be mocked, and a hard coded duration time on the frontend for dispatchers to answer. For simplicity, all incoming live calls will have the same hard coded duration time, which is also configurable on the frontend in the config page. The incoming call JSON will be serialized and sent to the async agent backend, where the Redis queue lives. The queue will be updated, which the frontend will poll and render.
Number of dispatchers that can answer calls.

If a call is an incoming human call, it will:
Go to the server 
Get transcribed 
Go through the AI agents
Get sorted through the queue 
Have the metadata sent to the frontend 

For the dashboard UI: when the user clicks on a list in the dashboard in the item, the frontend fetches the details from the backend and renders the details there. When a certain item is selected, that item is excluded from being selected by a dispatcher and having the timeOut() run. The user will then have a “resolve” button to click, which will call a DELETE endpoint to remove the item from the queue.
