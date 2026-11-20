// Copy this file to secrets.h and fill in local values. secrets.h is gitignored.
#pragma once

#define WIFI_SSID        "your-wifi-ssid"
#define WIFI_PASSWORD    "your-wifi-password"

// Base URL of the SENTINEL server. Use an HTTPS URL in production.
#define SENTINEL_URL     "http://192.168.1.50:5108"

// Must match GATEWAY_KEY in the server's .env.
#define SENTINEL_GATEWAY_KEY "gw-sentinel-demo-key"
