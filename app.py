#!/usr/bin/env python3
from flask import Flask, jsonify, request
import requests
import xarray as xr
import numpy as np
import io
import datetime
import os
import json

app = Flask(__name__)

# --- Configuration ---
DEFAULT_LAT = "0.000000"
DEFAULT_LON = "0.00000"
CACHE_DIR = "/cache" 

@app.route('/get_forecast', methods=['GET'])
def get_forecast():
    
    FMI_URL = "" 
    
    try:
        lat = request.args.get('lat', DEFAULT_LAT)
        lon = request.args.get('lon', DEFAULT_LON)

        today = datetime.datetime.now(datetime.timezone.utc)
        yesterday = today - datetime.timedelta(days=1)
        run_timestamp = yesterday.strftime("%Y-%m-%d") + "T00:00:00Z"
        
        cache_file_name = f"{run_timestamp}_{lat}_{lon}.json"
        cache_file = os.path.join(CACHE_DIR, cache_file_name)
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                return jsonify(cached_data)
            except Exception as e:
                pass 

        time_start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
        time_end = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H:00:00Z")

        FMI_URL = (
            f"https://thredds.silam.fmi.fi/thredds/ncss/grid/silam_europe_v6_0/runs/silam_europe_v6_0_RUN_{run_timestamp}"
            f"?var=cnc_PM2_5"
            f"&north={lat}&south={lat}"
            f"&west={lon}&east={lon}"
            f"&horizStride=1"
            f"&time_start={time_start}&time_end={time_end}"
            f"&accept=netcdf4-classic&addLatLon=true"
        )
        
        response = requests.get(FMI_URL)
        response.raise_for_status() 
        file_content = io.BytesIO(response.content)

        forecasts = {}
        with xr.open_dataset(file_content, engine="h5netcdf") as ds:
            pm25_data = ds['cnc_PM2_5']
            
            for t in pm25_data.time:
                value = pm25_data.sel(time=t).values.flatten()[0]
                hourKey = np.datetime_as_string(t, unit='s') + "Z"
                
                if np.isnan(value):
                    forecasts[hourKey] = None
                else:
                    micrograms = float(value) * 1e9
                    forecasts[hourKey] = micrograms

        with open(cache_file, 'w') as f:
            json.dump(forecasts, f)

        return jsonify(forecasts)

    except Exception as e:
        return jsonify({"error": str(e), "url_called": FMI_URL}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
