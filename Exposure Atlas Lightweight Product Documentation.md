# Exposure Atlas

## **TL;DR**

Exposure Atlas transforms your life’s digital exhaust — calendar events, location history, and photo metadata — into a personal exposure record, enriched with historical environmental data like AQI, UV index, and pollen. The MVP focuses on effortless uploads, quick enrichment, and two-three compelling, shareable insight cards, targeting quantified-self enthusiasts and health-curious professionals seeking actionable lifestyle feedback.

## ---

**Goals**

### **Team Goals**

* Ship a live demo that ingests at least one real user’s data and displays 2-3 insightful cards (P0).

* Validate user interest by having \>60% of demo participants rate insights as “useful” or “surprising.”

### **User Goals**

* Reveal how environmental exposures from places, time, and context have affected a user’s health and longevity.

* Export and share a digestible, visual insight with friends or health advisors.

### **Non-Goals**

* No provisioning of medical guidance or clinical recommendations.

* No development of real-time notification or alerting features at launch.

* No full biological age or global health metrics: we are exclusively focusing on exposure-driven narrative insights from surprising sources that have not been thought of as sources of longevity data before.

## ---

**User Stories**

**Personas:**

* Quantified-Self Enthusiast (QSE)

**Quantified-Self Enthusiast (QSE):**

* As a QSE, I want to upload my location history and calendar, so that I can see my exposure timeline without manual data entry.

* As a QSE, I want to compare exposure between home and office days, so that I can choose where to work on high-AQI days.

* As a QSE, I want to know how health-relevant exposures have differed between different places I have lived

* As a QSE, I want to know how the places I have visited have compared to where I was living at the time. Were those trips better for my health or worse?

## ---

**Functional Requirements**

* **Core Data Ingestion** (Priority: P0)

  * File upload for Google Location History (JSON); parse timestamps and geo-coordinates

  * File upload for iOS-exported GPX; parse timestamps and geo-coordinates

* **Stretch Data Ingestion** (Priority: P1)

  * ICS file upload for calendar events; match events to locations and time segments where possible

  * Photostream metadata ingest: parse timestamps and geo-coordinates from a tool a user runs separately on their photostream to upload *only* their metadata, not the photos themselves

* **Data Enrichment** (Priority: P0)

  * For each timestamped location, enrich with historical AQI, UV, and pollen data via weather APIs (daily/hourly).

  * Stretch goal: Cache API responses and batch queries by time/location to manage rate limits and cost.

* **Aggregations & Insights** (Priority: P0)

  * Aggregate and normalize daily/weekly exposure levels for AQI, UV, and pollen, with confidence scoring.

  * Generate Insight Card 1: "Commute Exposure vs. WFH," visualizing weekday location-linked exposure.

  * Generate Insight Card 2: "Travel Week Outlier," highlighting deviations from a baseline and a narrative explanation.

  * Generate Insight Card 3: “Hometown 1 vs Hometown 2,” comparing exposure levels for what appears to be two different places where a user has lived.

* **Visualization & Sharing** (Priority: P0)

  * Minimal dashboard showing exposure timeline, map heat strip, and 2-3 dynamic insight cards.

* **Sharing** (Priority: P2)

  * “Copy link” or export as PNG for card sharing; shareable links use ephemeral, privacy-safe storage.

* **Privacy & Controls** (Priority: P0)

  * By-default local or ephemeral processing; explicit “delete all” functionality.

  * Clear data provenance, showing data source lineage for every metric.

* **Other Stretch Features** (Priority: P2)

  * Display simple, anonymized cohort benchmarks by city or week (no PII shared).

## ---

**User Experience**

**Entry Point & First-Time User Experience**

* The landing page introduces the product promise and lists required files (e.g., Location JSON/KML, ICS calendar).

* Users see one clearly labeled CTA: “Build My Exposure Story.”

* Onboarding wizard steps:

  * User selects sources, drags and drops files, and reviews a quick summary of what data will be parsed and how it will be used.

**Core Experience**

* **Step 1:** Upload files.

  * Minimalist drag-and-drop UI, with immediate feedback on allowed file types and file parsing progress.

  * Validation for correct formats and file sizes; display counts of parsed datapoints/events.

  * On success, the experience continues to enrichment automatically.

* **Step 2:** Data Enrichment.

  * Visual progress: live counter of enrichment (API lookups, tiles processed) and estimated time remaining.

  * Graceful fallback to daily data resolution if hourly API quotas are exceeded.

  * Allow user to cancel, retry, or return to upload.

* **Step 3:** Dashboard Exploration.

  * Exposure Timeline: Stacked bands for AQI/UV/pollen, with hoverable details and confidence badges.

  * Map Heat Strip: Visualizes time spent per major location (darker \= more exposure).

  * Insight Cards: Three cards summarizing findings (“Commute vs. WFH,” “Travel Week Outlier,” “Hometown 1 vs Hometown 2”) including supporting chartlets and a narrative.

* **Step 4:** Share or Save.

  * User selects an insight card to export as PNG or gets a non-indexed share URL (if cloud enabled).

  * Option to delete all data or start over.

**Advanced Features & Edge Cases**

* If data is sparse, display a “Data completeness” badge and adjust confidence metrics.

## ---

**Narrative**

Jordan is a 34-year-old product manager who fits in twice-weekly runs and monthly business travel. Despite having years of detailed location history and a well-kept digital calendar, none of these sources provide any holistic view of how his daily life shapes his long term health prospects. During a lunch break, Jordan finds Exposure Atlas, drags and drops a Location History JSON and a calendar ICS file, and watches as the platform processes and enriches this history, layering in historical AQI, UV, and pollen readings matched to each segment of Jordan’s real timeline.

Within minutes, the dashboard surfaces two clear narratives. The first insight card reveals that on in-office days, Jordan’s commute leads to AQI spikes 2–3× higher than work-from-home days. The second card calls out a recent conference trip: an outlier week for both UV and pollen exposure, plus late nights. Satisfied, Jordan exports the “Commute Exposure vs. WFH” card to share with colleagues and opts in for monthly summaries.

Not only does Jordan leave with actionable feedback for the week ahead, but the team confirms a real potential for transforming digital “exhaust” into actionable health insights.

## ---

**Technical Considerations**

### **Technical Needs**

* **Front-end:** Single-page app supporting file upload, progress reporting, dashboard display, and chart/card export.

* **Back-end:** Lightweight server (if needed) for parsing, batch enrichment, caching API responses, ephemeral storage for shareable links.

* **Data model:** User session key, source files (location, calendar), time-mapped exposure records (lat/long, timestamp, AQI, UV, pollen, confidence), insights dictionary.

### **Integration Points**

* File formats: Google Location JSON/KML, GPX, ICS calendar, and photosteam metadata if a good tool is found for us to use.

* Historical weather/exposure APIs (with hourly/daily resolution, preferably free-tier compatible).

### **Data Storage & Privacy**

* Stretch goal default: Local/in-browser processing with no persistent cloud storage unless share/export is invoked.

* Share/export: 24-hour ephemeral server storage, with user-initiated delete-all available at any time.

* All file handling and results clearly documented in the UI; explicit user consent for any cloud activity; no third-party sharing.

### **Scalability & Performance**

* Optimize API calls: Group/bucket by tile and time window to minimize external requests.

* Implement caching to handle repetitive lookups and manage quota.

* Design for typical load of 1–2 users at a time (demo stage), but scalable logic for expansion.

### **Potential Challenges**

* We don’t yet know how to usefully aggregate all this exposure data into something truly insightful.

* Parsing and resolving inconsistent timestamp/timezone data across uploads.

* Handling API quota/rate limit issues and data gaps gracefully.

* Ensuring “exposure” narratives are clear and comprehensible to all users: definitions and caveats are included with each card.

* Managing ephemeral storage security for shareable links.

---

