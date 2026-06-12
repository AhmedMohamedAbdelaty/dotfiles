#!/bin/bash

# Simple weather notification (requires curl)
city="Cairo"  # Change to your city
api_key="your_api_key_here"  # Get from openweathermap.org

# For demo purposes, we'll create a mock weather notification
# In real use, you'd use: weather_data=$(curl -s "http://api.openweathermap.org/data/2.5/weather?q=$city&appid=$api_key&units=metric")

# Mock weather data for demo
temperature="25"
condition="Sunny"
humidity="60"
wind_speed="5"

weather_info="🌡️ Temperature: ${temperature}°C
🌤️ Condition: ${condition}
💧 Humidity: ${humidity}%
💨 Wind: ${wind_speed} m/s"

# Send notification
dunstify -a "weather" -u "normal" -i "weather-clear" -t 15000 \
    "🌍 Weather in $city" "$weather_info"
