# AI Agent Skills Specification

This document defines the skills and tool capabilities available to the LangGraph AI Agent powered by Gemini.

---

## 1. Browsing Skill (`browse_web`)

### Description
Allows the agent to search the web for real-time information, check schedules, research travel options, compare prices, or extract content from specific URLs.

### Capabilities
- **Web Search**: Query current information, news, flight/train schedules, prices, and weather.
- **Content Retrieval**: Inspect and extract text content from specified URLs.

### Tool Definition
- **Function Name**: `browse_web`
- **Parameters**:
  - `query` (*string*, required): Search term or query to look up information.
  - `url` (*string*, optional): Specific web page URL to inspect or extract data from.

### Example Usage Scenarios
- *"Find the latest flight options from New York to London for next Friday."*
- *"Look up the top-rated hotels in Tokyo near Shinjuku station."*
- *"Search for available train timings between Paris and Lyon."*

---

## 2. Ticket Booking Skill (`book_ticket`)

### Description
Enables the agent to process ticket reservations across multiple transport modes (Flights, Trains, Buses, Concerts/Movies). Generates verified booking references (PNR), calculates fares, and provides confirmation summaries.

### Capabilities
- Multi-mode ticketing: Flights, Trains, Buses, and Event/Movie tickets.
- Passenger details validation and ticket tier/class selection.
- Automatic PNR / Booking ID generation and itinerary creation.

### Tool Definition
- **Function Name**: `book_ticket`
- **Parameters**:
  - `category` (*string*, required): Type of ticket (`flight`, `train`, `bus`, `movie`, `event`).
  - `origin` (*string*, required): Departure city/location or venue.
  - `destination` (*string*, required): Arrival city/destination.
  - `date` (*string*, required): Travel or event date (e.g., `YYYY-MM-DD`).
  - `passengers` (*integer*, required): Number of tickets/passengers.
  - `passenger_names` (*list of strings*, required): Names of all passengers.
  - `ticket_class` (*string*, optional, default: `"Economy"`): Class tier (`Economy`, `Premium`, `Business`, `First`).

### Example Usage Scenarios
- *"Book 2 Economy flight tickets from San Francisco to Seattle on 2026-11-15 for John Doe and Jane Doe."*
- *"Book 1 train ticket from Berlin to Munich on 2026-12-01 for Alex Smith."*

---

## 3. Booking Status Skill (`check_ticket_status`)

### Description
Allows the agent to check, verify, and retrieve details for existing reservations using a booking ID or PNR.

### Capabilities
- Look up reservation details (origin, destination, date, class, passenger list).
- Verify booking confirmation status.

### Tool Definition
- **Function Name**: `check_ticket_status`
- **Parameters**:
  - `booking_id` (*string*, required): Unique reservation identifier (e.g. `FL-A1B2C3D4`).

### Example Usage Scenarios
- *"Check the status of my flight booking FL-A1B2C3D4."*
- *"Can you show the details for reservation TR-98765432?"*
