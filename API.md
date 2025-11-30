# Smart Farm IoT API Documentation

This document describes the HTTP API endpoints and Socket.IO events available in the Smart Farm IoT application.

## HTTP API

### Authentication
Most API endpoints require the user to be logged in via the web session, or are public if configured in `public_prefixes` in `app.py`.

### Endpoints

#### 1. Get Latest Sensor Data
Retrieves the latest data from all connected devices.

- **URL**: `/data_all` (or `/data`)
- **Method**: `GET`
- **Success Response**:
    - **Code**: 200 OK
    - **Content**: JSON object containing latest sensor readings for each device.
    ```json
    {
      "device1": {
        "temp": 28.5,
        "humi": 65.2,
        "sensor": "DHT22",
        "device_timestamp": "2023-10-27 10:00:00",
        "server_timestamp": "2023-10-27 10:00:05"
      },
      "timestamp": "2023-10-27 10:00:05"
    }
    ```

#### 2. Get Relay States
Retrieves the current status (on/off) of all relays.

- **URL**: `/api/relay_states`
- **Method**: `GET`
- **Success Response**:
    - **Code**: 200 OK
    - **Content**: JSON array of relay objects.
    ```json
    [
      {"relayId": "1", "state": "on"},
      {"relayId": "2", "state": "off"}
    ]
    ```

#### 3. Control Relay
Turns a specific relay ON or OFF.

- **URL**: `/api/relay_control`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**:
    ```json
    {
      "relay": "1",
      "state": "on"
    }
    ```
- **Success Response**:
    - **Code**: 200 OK
    - **Content**: `{"success": true, "relay": "1", "state": "on"}`

#### 4. Get Historical Data
Retrieves historical sensor data for a specific device.

- **URL**: `/api/history`
- **Method**: `GET`
- **Query Parameters**:
    - `device`: Device ID (default: `device1`)
    - `start`: Start date (YYYY-MM-DD)
    - `end`: End date (YYYY-MM-DD)
- **Success Response**:
    - **Code**: 200 OK
    - **Content**: JSON array of historical data points.

#### 5. Get Soil Data
Retrieves the latest soil sensor data.

- **URL**: `/soil_data`
- **Method**: `GET`
- **Success Response**:
    - **Code**: 200 OK
    - **Content**: JSON object with soil parameters.

## Socket.IO Events

The application uses Socket.IO for real-time bidirectional communication.

### Client -> Server Events

#### `toggle_relay`
Request to toggle the state of a relay.
- **Data**: `{"relay_id": "1"}`
- **Description**: Toggles the relay state (ON -> OFF or OFF -> ON).

### Server -> Client Events

#### `sensor_update`
Broadcasted when new sensor data is received via MQTT.
- **Data**: JSON object with latest sensor data (same structure as `/data_all`).

#### `relay_status`
Broadcasted when a relay state changes.
- **Data**: `{"relay": "1", "state": "on"}`

#### `relay_error`
Sent to a specific client if an error occurs during relay control.
- **Data**: `{"message": "Error description...", "relay_id": "1"}`
