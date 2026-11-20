# SENTINEL IoT Disaster Command System - Viva Questions & Answers

## Project Overview
Q1. What is SENTINEL?
A: IoT-based early warning and disaster management system for real-time monitoring, risk assessment, alerting, and coordinated emergency response.

Q2. Why this project?
A: Bridges gap between IoT sensors, risk analysis, and authority decision-making with transparent, auditable system.

Q3. What technologies used?
A: Node.js, Express, React, Vite, SQLite, WebSocket, Leaflet, ESP32/LoRa

## Hardware & IoT
Q4. What sensors used?
A: DHT22 (Temp/Humidity), LM393 Rain Sensor, HC-SR04 Ultrasonic (Water Level), SW-420 Vibration, MQ-135 (AQI), GY-NEO6MV2 GPS, SOS Button, Battery Monitor

Q5. How does LoRa help?
A: Long range, low power communication ideal for remote disaster-prone areas

## Risk Engine
Q6. How does risk calculation work?
A: Rule-based weighted scoring with ramp normalization, terrain multipliers, compound hazard detection, SOS override

Q7. What are risk levels?
A: Low (<25), Moderate (25-49), High (50-74), Severe (>=75)

Q8. What is compound hazard?
A: When flood >=50 and landslide >=50 simultaneously, add +6 to score

## Software Architecture
Q9. How does real-time work?
A: WebSocket for live updates, REST APIs for commands

Q10. Database choice?
A: SQLite (lightweight, embedded, perfect for edge deployment)

## Security
Q11. Security measures?
A: JWT auth, role-based access, rate limiting, helmet, CORS, input validation, XSS protection

## Features
Q12. Evacuation routing?
A: Finds nearest shelter using Haversine, provides Google/Apple/Waze directions

Q13. Multi-role system?
A: Citizen, Employee, Admin, Owner with different access levels

## ML & Accuracy
Q14. ML integration?
A: Trained model with 10000 samples, MAE ~2.38, RMSE ~2.98

## Deployment
Q15. Deployment ready?
A: Render, GitHub Actions CI/CD configured

## Challenges & Solutions
Q16. Main challenges?
A: Real-time sync, risk calibration, sector switching, auth integration

Q17. Future scope?
A: SMS/Email alerts, mobile app (Capacitor), ML prediction, satellite integration
