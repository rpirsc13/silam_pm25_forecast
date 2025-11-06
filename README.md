# SILAM PM2.5 Forecast Service

This is a self-contained, Dockerized Python microservice that acts as a "translator" for complex scientific air quality data.

Its sole purpose is to fetch raw PM2.5 forecast data from the Finnish Meteorological Institute (FMI) SILAM model and convert it into a simple, clean JSON API.

This service is designed to be called by other platforms—like **Node-RED**, **Home Assistant**, or any custom script—that need easy access to this data but can't be bothered to parse `netcdf` files.

## The Problem (Why This Exists)

The FMI SILAM server has fantastic, high-quality forecast data. The problem? It's... difficult.

* **Format:** The data is in `netcdf4-classic`, a binary scientific format.
* **Accessibility:** Most automation platforms can't read `netcdf` files.
* **Data Structure:** The data is a 3D model, including multiple altitude levels, not just the ground-level data we want.
* **Units:** The concentration unit is in $kg/m^3$ (e.g., `8.14e-9`), not the user-friendly $µg/m^3$.

## The Solution (What This Service Does)

This service provides a single, simple API endpoint: `GET /get_forecast`.

When called, the Python service does all the heavy lifting:
1.  **Smart Caching:** It checks for a local cache file for today's forecast (based on date and coordinates). If found, it returns the cached data instantly.
2.  **Fetches Data:** If no cache exists, it builds and calls the FMI THREDDS URL to fetch the latest data run.
3.  **Parses in Memory:** It downloads the binary `netcdf` file and parses it in memory using `xarray` and `h5netcdf`.
4.  **Extracts Data:** It intelligently extracts the *ground-level* PM2.5 value, ignoring the other altitude layers.
5.  **Converts Units:** It automatically converts the units from $kg/m^3$ to $µg/m^3$ (e.g., `8.14e-9` -> `8.14`).
6.  **Saves to Cache:** It saves the final, clean JSON to its cache file for future requests.
7.  **Returns Clean JSON:** It returns the clean, simple JSON to whatever service called it.

---

## Getting Started

### 1. Project Files

This repository contains three key files:

* **`app.py`**: The main Python Flask application that runs the server, handles API requests, and performs all the parsing and caching logic.
* **`requirements.txt`**: A list of all the Python dependencies (`flask`, `xarray`, `h5netcdf`, etc.) needed to run the app.
* **`Dockerfile`**: A set of instructions to build a lightweight, self-contained Docker image with the app and all its dependencies. It also creates the `/cache` directory.

### 2. Build & Run with Docker

This project is designed to be run as a Docker container.

1.  **Build the image:**
    From the root of this repository, build the Docker image:
    ```bash
    docker build -t silam-forecast .
    ```

2.  **Run with `docker-compose` (Recommended):**
    Add the service to your `docker-compose.yml` file. This is the easiest way to manage it, especially if you're running Node-RED or Home Assistant in Docker.

    ```yaml
    version: '3.7'
    
    services:
      # ... your other services (Home Assistant, Node-RED, etc.)
    
      forecast_service:
        container_name: forecast_service
        # If you built it locally:
        image: silam-forecast:latest
        # Or, if you push to a registry, use:
        # build: ./path/to/forecast_service
        restart: unless-stopped
        ports:
          - "5000:5000" # Expose port 5000 to the host
        networks:
          - your_network_name # Your existing network
    
    networks:
      your_network_name:
        # ... your network config
    ```
    Then, just run `docker-compose up -d forecast_service`.

3.  **Run with `docker run` (Simple):**
    ```bash
    docker run -d \
      --name forecast_service \
      -p 5000:5000 \
      --restart unless-stopped \
      silam-forecast
    ```

The service is now running on your Docker host at port 5000.

---

## API Usage

The Python service is now running on your network. Your other services (like Node-RED) can now call it.

### `GET /get_forecast`
Returns the full 5-day, hourly forecast as a JSON object.

**Optional Query Parameters:**
* `lat` (float): Latitude to query.
* `lon` (float): Longitude to query.

**Example Calls:**
* `http://127.0.0.1:5000/get_forecast`
    (Uses the default coordinates hardcoded in `app.py`)
* `http://127.0.0.1:5000/get_forecast?lat=40.7128&lon=-74.0060`
    (Gets forecast for New York)

**Success Response (200 OK):**
```json
{
  "2025-11-06T09:00:00Z": 8.14173972685239,
  "2025-11-06T10:00:00Z": 9.62853707875411,
  "2025-11-06T11:00:00Z": 11.229496443832,
  "...": "..."
}
