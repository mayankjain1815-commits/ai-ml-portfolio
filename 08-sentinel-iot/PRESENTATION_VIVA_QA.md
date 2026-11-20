# SENTINEL - Presentation & Viva Q&A (Complete)

## 1. INTRODUCTION (Slide 1)
**Q1. What is SENTINEL?**
A: SENTINEL is an IoT-based Early Warning and Disaster Management System that monitors environmental parameters, assesses disaster risk in real-time, generates alerts, and guides people to safety during floods, landslides, poor air quality, and heatwaves.

**Q2. Why "SENTINEL"?**
A: Like a sentinel/watchman, it constantly monitors, detects threats early, and alerts authorities/people before disaster strikes.

**Q3. What inspired this project?**
A: India faces frequent floods/landslides. Need for automated early warning system bridging sensors, analysis, and response.

## 2. PROBLEM STATEMENT & OBJECTIVES (Slide 2)
**Q4. What is the problem statement?**
A: Lack of integrated system connecting IoT sensors, risk analysis, alerting, and evacuation - leading to delayed response.

**Q5. Main objectives?**
A: Real-time monitoring, transparent risk assessment, instant alerts, authority control, evacuation routing, audit trail.

**Q6. Scope of project?**
A: IoT sensor network, web dashboard, mobile-friendly, multi-role access, evacuation guidance.

## 3. LITERATURE REVIEW / EXISTING SYSTEM (Slide 3)
**Q7. Existing systems vs ours?**
A: Existing are mostly alert-only. Ours is end-to-end: sensing->risk->alert->command->evacuation with explainability.

**Q8. What's unique?**
A: Explainable risk engine, compound hazard detection, authority override with audit, GPS-based evacuation to shelters with map integration.

## 4. HARDWARE COMPONENTS (Slide 4)
**Q9. Why ESP32?**
A: Dual core, WiFi+BLE, more GPIO, low cost, good for IoT.

**Q10. Why LoRa?**
A: Long range up to 10km, penetrates obstacles, low power, works where GSM weak.

**Q11. Explain each sensor?**
A: DHT22-temp/humidity, LM393-rainfall, HC-SR04-water level, SW-420-vibration, MQ-135-air quality, GY-NEO6MV2-GPS, SOS button, LiPo+battery monitor

**Q12. How are they powered?**
A: Solar panel + LiPo battery with charging circuit

**Q13. Gateway role?**
A: Receives LoRa data, forwards to server via HTTP/WebSocket

## 5. SOFTWARE TECHNOLOGY (Slide 5)
**Q14. Frontend choices?**
A: React 19 for component-based UI, Vite for fast builds

**Q15. Backend choices?**
A: Node.js+Express for REST/WebSocket, handles real-time

**Q16. Database?**
A: SQLite - file-based, portable, ACID, sufficient for this application

**Q17. Why Leaflet?**
A: Open source, lightweight, customizable, works offline

## 6. SYSTEM ARCHITECTURE (Slide 6)
**Q18. Explain data flow?**
A: Sensor->ESP32->LoRa->Gateway->Server(API/WS)->DB->Risk Engine->Alerts->Dashboard

**Q19. What is risk engine?**
A: Core logic calculating 0-100 risk using weighted sensors

**Q20. How real-time achieved?**
A: WebSocket pushes updates to all connected clients

## 7. RISK ASSESSMENT ALGORITHM (Slide 7)
**Q21. Explain in detail?**
A: For each hazard compute weighted sum of normalized values, apply terrain multiplier, check compound condition, pick highest as primary, apply SOS override if present

**Q22. Why weighted approach?**
A: Different parameters have different importance based on domain knowledge

**Q23. Risk classification?**
A: <25 Low, 25-49 Moderate, 50-74 High, >=75 Severe

**Q24. Validation?**
A: Tested with simulated scenarios, all tests pass

## 8. FEATURES IMPLEMENTED (Slide 8)
**Q25. Key features?**
A: Live dashboard, interactive map, alerts, incident log, command console, auth, evacuation routing, multi-role, sector switching

**Q26. Authority console features?**
A: Acknowledge alerts, override risk, evacuation/all-clear, siren, SOS test

**Q27. Evacuation system?**
A: Get location -> find nearest shelter -> route via Google/Apple/Waze Maps

**Q28. Multi-role system?**
A: Citizen (view+route), Employee (monitor), Admin (command), Owner (management)

## 9. SECURITY IMPLEMENTATION (Slide 9)
**Q29. How secured?**
A: JWT tokens, role-based access control, password hashing, rate limiting, helmet headers, CORS, input validation with Zod

**Q30. What is RBAC?**
A: Role-Based Access Control - different permissions per role

## 10. TESTING & RESULTS (Slide 10)
**Q31. Testing done?**
A: Unit tests (risk engine, validation), API tests, integration tests - 38/38 passing

**Q32. Results?**
A: Working prototype with all features, accurate risk calculation, real-time updates

## 11. ADVANTAGES & APPLICATIONS
**Q33. Advantages?**
A: Early warning, automated assessment, transparent, scalable, cost-effective, explainable

**Q34. Applications?**
A: Flood-prone areas, hilly regions, smart cities, disaster management cells, NDMA/state authorities

**Q35. Can be used in other disasters?**
A: Can extend to cyclones, earthquakes (with different sensors)

## 12. FUTURE SCOPE
**Q36. Future enhancements?**
A: SMS/Email/WhatsApp alerts, ML prediction, mobile app, satellite imagery, siren integration, more sensors

**Q37. Scalability plans?**
A: PostgreSQL, cloud deployment, multiple regions

## 13. CONCLUSION
**Q38. Conclusion?**
A: Successfully developed IoT-based disaster management system providing early warning, risk assessment, and evacuation guidance - can save lives through timely alerts.

**Q39. What did you learn?**
A: IoT, embedded systems, full-stack, real-time, security, project management

**Q40. Any challenges faced?**
A: Sensor calibration logic, real-time sync, auth integration, map rendering - all resolved
