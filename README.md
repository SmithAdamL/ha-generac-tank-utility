# Generac Tank Utility Integration (v0.1.0)

IMPORTANT UPDATE: 6/7/2025 - This integration is no longer going to be supported.  "The Tank Utility team has been acquired by ANOVA and is no longer part of Generac"  This integration worked on the legacy Tank Utility API's and Generac Mobile Link support has failed to respond to my requests for API information.


A Home Assistant custom integration for monitoring Tank Utility (Generac) propane tank monitors. This integration uses Home Assistant’s UI config flow with Basic Authentication to connect to your Tank Utility account, retrieve detailed sensor data (fuel level, temperature, battery status, etc.), and supports per‑tank configurable polling intervals.

> **Note:** MQTT publishing is in the process of being implemented in the code and shows in the configuation, but is not in use at this time.

## Features

- **Secure Authentication:** Uses BasicAuth to obtain an API token from Tank Utility.
- **Device Discovery:** Automatically discovers all tank devices associated with your account.
- **Per-Tank Polling:** Each tank uses a default polling interval (6 hours) that can be configured per device.
- **Sensor Entities:** Provides sensors for:
  - **Fuel Level:** Current fill level (%) of the tank.
  - **Temperature:** Ambient or device temperature in °F.
  - **Battery:** Displays the battery status as returned by the API (e.g. "good", "low", "critical").
- **Binary Sensor Entities:** Provides alerts for low conditions:
  - **Low Fuel:** On when fuel level is ≤ 20%.
  - **Low Battery:** On when battery status is "low" or "critical".
- **Comprehensive Logging:** Detailed debug and error logs assist in troubleshooting connectivity, authentication, and data issues.

## Manual Installation

1. **Download the Integration:**
   - Clone the repository or download the files from:
     ```
     https://github.com/SmithAdamL/ha-generac-tank-utility
     ```

2. **Copy Files:**
   - Ecopy the entire `generac_tank_utility` folder into your Home Assistant `custom_components` directory.
   - Example HA path: `/config/custom_components/generac_tank_utility`

3. **Restart Home Assistant:**
   - Restart Home Assistant to load the integration.

4. **Configure the Integration:**
   - Navigate to **Settings → Devices & Services → Add Integration**.
   - Search for **Generac Tank Utility**.
   - Enter your Tank Utility account **email** and **password** when prompted.
   - The integration will automatically discover your tank device(s) and create the necessary sensor and binary sensor entities.

## Configuration

After installation, you can adjust the polling intervals for each device through the integration's options (via the UI). Currently, the MQTT publishing feature shown is reserved for future releases and is not in use at this time. 

## Troubleshooting

- **Logging:** Enable debug logging for `custom_components.generac_tank_utility` to view detailed API interactions and error messages.
- **Reauthentication:** If your credentials change or expire, Home Assistant will prompt you to reauthenticate.

## Repository

For more details, reporting issues, or contributing, please visit:  
[https://github.com/SmithAdamL/ha-generac-tank-utility](https://github.com/SmithAdamL/ha-generac-tank-utility)
