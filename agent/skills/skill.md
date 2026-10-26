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

## 2. Platform Selection Skill (`get_booking_platforms`)

### Description
Retrieves curated, verified booking platforms and direct reservation links for travel (flights, trains, buses), entertainment (movies, concerts, events), and accommodations.
**CRITICAL POLICY**: The agent must NEVER directly book tickets on its own. It must provide platform options and direct clickable links, prompting the user to select their preferred platform first.

### Capabilities
- Retrieves trusted platforms (Google Flights, Skyscanner, MakeMyTrip, IRCTC, Trainline, RedBus, FlixBus, BookMyShow, Ticketmaster, etc.).
- Produces customized direct search links with destination, route, and date parameters.
- Prompts user to choose their preferred booking platform and click the link to proceed.

### Tool Definition
- **Function Name**: `get_booking_platforms`
- **Parameters**:
  - `category` (*string*, required): Mode of transport or event (`flight`, `train`, `bus`, `movie`, `event`, `hotel`).
  - `origin` (*string*, optional): Departure location or venue.
  - `destination` (*string*, optional): Arrival location or event name.
  - `date` (*string*, optional): Date (`YYYY-MM-DD`).

---

## 3. Ticket Booking Skill (`book_ticket`)

### Description
Registers ticket reservations **only after the user has selected their preferred booking platform**. Direct automated booking without platform selection is blocked. Saves internal itinerary drafts (`AGT-FL-XXXX`) and can also register **real official carrier PNRs** (e.g. 10-digit IRCTC or 6-character Airline PNR) received after booking on the platform.

### Capabilities
- Multi-mode ticketing: Flights, Trains, Buses, and Event/Movie tickets.
- Requires explicit user-selected `platform`.
- Supports optional `official_pnr` received from carrier platform.
- Passenger details validation and ticket tier/class selection.
- Clear distinction between internal itinerary references and carrier GDS PNRs.

### Tool Definition
- **Function Name**: `book_ticket`
- **Parameters**:
  - `category` (*string*, required): Type of ticket (`flight`, `train`, `bus`, `movie`, `event`).
  - `origin` (*string*, required): Departure city/location or venue.
  - `destination` (*string*, required): Arrival city/destination.
  - `date` (*string*, required): Travel or event date (e.g., `YYYY-MM-DD`).
  - `passengers` (*integer*, required): Number of tickets/passengers.
  - `passenger_names` (*list of strings*, required): Names of all passengers.
  - `platform` (*string*, required): The booking platform selected by the user (e.g., `"Google Flights"`, `"MakeMyTrip"`, `"IRCTC"`).
  - `official_pnr` (*string*, optional): Real carrier PNR received from the platform website (e.g. 10-digit IRCTC or 6-character airline PNR).
  - `ticket_class` (*string*, optional, default: `"Economy"`): Class tier (`Economy`, `Premium`, `Business`, `First`).

### Example Usage Scenarios
- User: *"Book a flight from San Francisco to Seattle on 2026-11-15"* ➔ Agent invokes `get_booking_platforms` and tells user to select a platform with clickable links.
- User: *"I choose Google Flights"* ➔ Agent invokes `book_ticket(platform="Google Flights")` saving an itinerary draft (`AGT-FL-XXXX`) and directing user to complete checkout for official PNR.
- User: *"I completed my booking on IRCTC, my PNR is 4521369874"* ➔ Agent registers official PNR `4521369874` with live tracking links.

---

## 4. Booking Status Skill (`check_ticket_status`)

### Description
Allows the agent to check, verify, and retrieve details for existing reservations using an internal agent reference or an official carrier PNR (e.g. Indian Railways 10-digit PNR, Airline 6-character PNR). Automatically provides direct official live verification portal links (ConfirmTkt, IRCTC, CheckMyTrip, Airline portals).

### Capabilities
- Look up reservation details (origin, destination, date, class, passenger list).
- Format detection: Identifies 10-digit IRCTC train PNRs and 6-character IATA Airline PNRs.
- Real-time portal links: Connects users to official live verification systems.
- Distinguishes internal agent draft references from official airline/railway GDS PNRs.
- Verify booking confirmation status.

### Tool Definition
- **Function Name**: `check_ticket_status`
- **Parameters**:
  - `booking_id` (*string*, required): Unique reservation identifier (e.g. `FL-A1B2C3D4`).

### Example Usage Scenarios
- *"Check the status of my flight booking FL-A1B2C3D4."*
- *"Can you show the details for reservation TR-98765432?"*

---

## 4. Gmail Notification Skill (`send_booking_email` & `send_email`)

### Description
Allows the agent to deliver official booking confirmation itineraries directly to passenger email addresses via Gmail SMTP. Sends both rich responsive HTML formatted emails (with route maps, class, passenger names, and booking status badges) and accessible plaintext versions. Also supports sending general notifications.

### Capabilities
- Automatic booking lookup from `booking_id` with full itinerary composition.
- Rich HTML email formatting suitable for mobile & desktop email clients.
- Universal Gmail delivery via standard TLS/SSL SMTP with Google App Passwords.
- Graceful test/dry-run preview mode when credentials are pending configuration.

### Tool Definitions

#### A. Send Booking Confirmation (`send_booking_email`)
- **Function Name**: `send_booking_email`
- **Parameters**:
  - `recipient_email` (*string*, required): Destination email address (e.g. `passenger@gmail.com`).
  - `booking_id` (*string*, required): The reservation reference ID (e.g. `FL-A1B2C3D4`).
  - `subject` (*string*, optional): Custom email subject line.
  - `additional_notes` (*string*, optional): Special instructions, luggage notes, or seat requests.

#### B. Send General Notification (`send_email`)
- **Function Name**: `send_email`
- **Parameters**:
  - `recipient_email` (*string*, required): Destination email address.
  - `subject` (*string*, required): Email subject line.
  - `body` (*string*, required): Plaintext email message body.

### Example Usage Scenarios
- *"Book 1 flight ticket to London for Jane Doe and email the confirmation to jane.doe@example.com."*
- *"Please send the itinerary for booking FL-8A3F12C9 to my email alex@gmail.com."*

