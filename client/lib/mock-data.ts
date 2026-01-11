/**
 * Mock transcript data for simulation initialization.
 * Compatible with POST /invoke endpoint.
 */

export interface TranscriptIn {
  text: string;
  time: string;
  location: string;
  duration: string;
}

export const mockTranscripts: TranscriptIn[] = [
  {
    text: "My house is on fire! I need help immediately. The address is 123 Maple Street, apartment 4B.",
    time: "2026-01-10T09:15:00Z",
    location: "V6B1A1",
    duration: "00:35",
  },
  {
    text: "There is an armed robbery happening at the convenience store on King Street. The suspect has a gun and is threatening the cashier. Please send help immediately!",
    time: "2026-01-10T14:30:00Z",
    location: "M5H2N2",
    duration: "03:52",
  },
  {
    text: "There is a group of people making a lot of noise outside my apartment. It's 2 AM and they are being really loud with music.",
    time: "2026-01-10T02:00:00Z",
    location: "K1A0B1",
    duration: "01:20",
  },
  {
    text: "Help! The convenience store on the corner of Sainte-Catherine and a guy has a gun, he's robbing the place!",
    time: "2026-01-10T18:45:00Z",
    location: "H2Y1C6",
    duration: "00:19",
  },
  {
    text: "My car was just stolen. It's a blue Honda Civic, license plate... I don't remember. From the street parking on Granville.",
    time: "2026-01-10T19:00:00Z",
    location: "V6B4Y8",
    duration: "00:11",
  },
  {
    text: "There's a party next door and it's so loud, the music is shaking my windows. It's been hours.",
    time: "2026-01-10T20:30:00Z",
    location: "T2P2V6",
    duration: "00:04",
  },
  {
    text: "I think my wallet was just stolen. I was in the ByWard Market and someone bumped into me.",
    time: "2026-01-10T20:00:00Z",
    location: "K1P1J1",
    duration: "00:06",
  },
  {
    text: "Someone broke my back window and is inside my house, I can hear them downstairs.",
    time: "2026-01-10T22:15:00Z",
    location: "R3B0N2",
    duration: "00:09",
  },
  {
    text: "There's a massive fire spreading through the industrial district. Multiple buildings are involved!",
    time: "2026-01-10T23:00:00Z",
    location: "L5N3C2",
    duration: "00:45",
  },
  {
    text: "A crowd has gathered at the stadium exit and people are being pushed. Someone might get hurt!",
    time: "2026-01-10T21:30:00Z",
    location: "M4W3X8",
    duration: "00:22",
  },
  {
    text: "I just witnessed a car break-in at the parking garage on Bay Street. The suspect is still there!",
    time: "2026-01-10T19:45:00Z",
    location: "M5J2N8",
    duration: "00:15",
  },
  {
    text: "There's someone trespassing in the construction site across the street. They're acting suspicious.",
    time: "2026-01-10T01:30:00Z",
    location: "V5K0A1",
    duration: "00:08",
  },
];
