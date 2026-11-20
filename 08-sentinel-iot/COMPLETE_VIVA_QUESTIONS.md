# COMPLETE VIVA QUESTIONS FOR SENTINEL IOT DISASTER COMMAND SYSTEM

## A. PROJECT INTRODUCTION (Easy)
1. **Q:** What is your project title?
   **A:** SENTINEL - IoT Early Warning and Disaster Management System

2. **Q:** What problem does it solve?
   **A:** Provides real-time disaster monitoring, early warning, risk assessment and coordinated evacuation for flood, landslide, air quality and heat hazards.

3. **Q:** Why did you choose this project?
   **A:** To bridge IoT sensors with emergency response for faster, data-driven disaster management.

4. **Q:** What is the objective?
   **A:** To create an end-to-end system from sensor data to alerts to evacuation guidance.

## B. HARDWARE & SENSORS (Technical)
5. **Q:** Which microcontroller used?
   **A:** ESP32

6. **Q:** Why ESP32?
   **A:** WiFi+Bluetooth, low power, enough GPIOs, affordable

7. **Q:** Why LoRa for communication?
   **A:** Long range (2-15km), low power, works in areas with poor connectivity

8. **Q:** List all sensors with purpose
   **A:** DHT22(Temp/Humidity), LM393(Rain), HC-SR04(Water level), SW-420(Vibration), MQ-135(AQI), GY-NEO6MV2(GPS), Push button(SOS), Voltage divider(Battery)

9. **Q:** How is water level measured?
   **A:** Ultrasonic sensor HC-SR04 measures distance, converted to water level

10. **Q:** How does SOS work?
   **A:** Physical button triggers immediate alert with 100% risk score

## C. SOFTWARE & ARCHITECTURE
11. **Q:** Tech stack?
   **A:** Frontend: React 19, Vite 7; Backend: Node.js 22, Express 5; DB: SQLite; Real-time: WebSocket

12. **Q:** Why Node.js?
   **A:** JavaScript full-stack, good for real-time, async I/O

13. **Q:** Why SQLite?
   **A:** Lightweight, serverless, no separate DB server needed, perfect for this scale

14. **Q:** What is WebSocket used for?
   **A:** Real-time bidirectional communication for live dashboard updates

15. **Q:** Explain system architecture
   **A:** Sensors -> ESP32/LoRa Gateway -> REST/WebSocket -> Backend (Validation, Risk Engine) -> SQLite -> React Dashboard

## D. RISK ENGINE & ALGORITHM
16. **Q:** What algorithm used for risk calculation?
   **A:** Rule-based weighted multi-criteria scoring with ramp normalization

17. **Q:** Explain ramp function
   **A:** Maps sensor value to 0-100 between onset and saturation points

18. **Q:** What are weights?
   **A:** Flood: Water 55%, Rain 30%, Humidity 8%, Trend 7%; Landslide: Rain 50%, Vibration 20%, Slope 20%, Humidity 10%

19. **Q:** What is compound hazard?
   **A:** When flood>=50 AND landslide>=50, add +6 points

20. **Q:** How is terrain handled?
   **A:** Terrain multipliers (riverine 1.12 for flood, slope 1.12 for landslide)

21. **Q:** Difference between sensor risk and effective risk?
   **A:** Effective risk can be overridden by authority, sensor risk preserved for audit

## E. FEATURES & FUNCTIONALITY
22. **Q:** What views in dashboard?
   **A:** Overview, Map, Alerts, Incidents, Command Console

23. **Q:** What is alert deduplication?
   **A:** One active alert per (node, hazard) type

24. **Q:** What is hysteresis in alerts?
   **A:** Needs 2 consecutive readings below threshold to clear high/severe alerts

25. **Q:** Evacuation routing feature?
   **A:** GPS-based location -> nearest shelter -> Google/Apple/Waze directions

26. **Q:** Multi-role authentication?
   **A:** Citizen, Employee, Admin, Owner with role-based access

27. **Q:** Sector switching?
   **A:** Can switch between different regions/basins

## F. SECURITY
28. **Q:** Security measures implemented?
   **A:** JWT authentication, bcrypt, role-based authorization, rate limiting, helmet, CORS, Zod validation

29. **Q:** Why JWT?
   **A:** Stateless authentication, secure token-based access

30. **Q:** How are passwords stored?
   **A:** Using bcryptjs with salting

## G. ML & DATA
31. **Q:** ML model used?
   **A:** Trained rule-calibrated model on synthetic data, MAE 2.38, RMSE 2.98

32. **Q:** How to improve accuracy?
   **A:** Collect real field data, retrain weights, use historical validation

## H. DEPLOYMENT & TESTING
33. **Q:** How many tests?
   **A:** 38 tests covering risk engine, validation, API, WebSocket

34. **Q:** Deployment options?
   **A:** Render, GitHub, can convert to mobile app with Capacitor

35. **Q:** PWA support?
   **A:** Yes, manifest.json added for installable app

## I. TOUGH QUESTIONS
36. **Q:** Why not use ML for everything?
   **A:** Rule-based is explainable, auditable for disaster response. ML can be biased. We use hybrid approach.

37. **Q:** How to handle false alerts?
   **A:** Hysteresis, deduplication, authority can override/acknowledge

38. **Q:** Scalability?
   **A:** Can add more nodes, use PostgreSQL for large scale, horizontal scaling

39. **Q:** What if internet fails?
   **A:** LoRa can work offline, local gateway storage possible

40. **Q:** Future enhancements?
   **A:** SMS/Email/WhatsApp alerts, mobile app, satellite data, AI prediction, integration with NDMA

## TEAM QUESTIONS
41. **Q:** Individual contribution?
   **A:** [Mention your specific role]

42. **Q:** Biggest learning?
   **A:** IoT integration, real-time systems, full-stack development

43. **Q:** What differentiates this?
   **A:** Complete end-to-end solution with explainable AI, evacuation routing, multi-role system
