# SIH Judge Review - SENTINEL IoT Disaster Command (Harsh Truth)

## Overall Verdict
**Score: 8.2/10** (Strong concept, good execution in parts. Needs hardening for production/SIH demo readiness)

## What's Good
- Clean concept: closes loop from sensors -> risk engine -> alerts -> command
- Deterministic, explainable risk engine with factors
- Real-time (WebSocket) + REST
- Good UI aesthetic with strict palette
- ESP32/LoRa integration docs present
- Tests for core logic exist
- Auth/roles added recently

## Critical Issues (Must Fix)

### 1) Tests Failing
- API tests fail because we added auth on command routes (siren/test-sos/ack/evac/override) but tests don't send tokens. 
  - Fix: update tests to send auth tokens or make routes configurable for tests. Or add test bypass. 
- Must get all tests passing.

### 2) Authentication Gaps
- Many command routes now require auth (good) but:
  - Frontend doesn't enforce login properly in some flows? We added login but need to ensure all mutating calls include token.
  - Default creds in .env - must force strong creds or warn.
  - No token refresh/expiry handling in UI.
  - `/api/auth/me` exists but not used.

### 3) Sector Switching
- Backend added but nodes don't change when switching sectors - still using same DB nodes. 
- Need to reload nodes/alerts/incidents per sector or have sector-scoped data.
- UI reloads but data may be stale.

### 4) Map
- Only Nashik custom basemap. Need India full map support.
- Need state/city/village/town coverage. Consider GeoJSON for India states/districts/blocks.
- Add search, routing to shelters, evacuation paths.

### 5) Notifications
- No SMS/email/push/WhatsApp integration. Need multi-channel alerts.
- No templates, escalation rules, contact groups.
- No delivery status tracking.

### 6) Population & Shelters
- Population shown as estimates. Need proper population DB, shelters with capacity, nearest shelter calculation.
- Need routing (shortest path) with distance/time to safest place.

### 7) Error Handling
- Some routes need better validation.
- CORS needs strict origins in prod.

## UI/UX Issues
- Profile/login added but not fully integrated everywhere.
- Some icons not clickable as requested.
- Mobile responsiveness needs testing.
- Loading states inconsistent.

## Recommendations
1. Fix failing tests immediately
2. Make sector switching load sector-specific data
3. Add India GeoJSON + admin boundaries
4. Add notification service (SMS/Email/Push) with templates
5. Add shelter/routing with population management
6. Add ML weight training pipeline (with evaluation metrics)
7. Make app-ready (PWA/Capacitor) structure
8. Prepare for Render/GitHub deploy
