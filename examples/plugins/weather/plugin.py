"""Weather plugin — looks up current weather using OpenWeatherMap API."""

from __future__ import annotations

import httpx

from zenbot.plugins.base import (
    PermissionLevel,
    PluginBase,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginResultStatus,
)

API_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherPlugin(PluginBase):
    """Looks up current weather for a given location."""

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="weather",
            version="1.0.0",
            description="Look up current weather by location",
            author="zenbot-team",
            network_domains=["api.openweathermap.org"],
            filesystem=PermissionLevel.NONE,
            secrets=["OPENWEATHER_API_KEY"],
            timeout_seconds=10.0,
        )

    async def handle(self, ctx: PluginContext) -> PluginResult:
        api_key = ctx.secrets.get("OPENWEATHER_API_KEY")
        if not api_key:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error="OPENWEATHER_API_KEY not configured. "
                "Run `zenbot credentials set OPENWEATHER_API_KEY`.",
            )

        location = ctx.user_input.strip()
        if not location:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error="Please provide a location (e.g., 'London' or 'Tokyo').",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    API_URL,
                    params={
                        "q": location,
                        "appid": api_key,
                        "units": "metric",
                    },
                )

                if response.status_code == 404:
                    return PluginResult(
                        status=PluginResultStatus.ERROR,
                        error=f"Location '{location}' not found.",
                    )

                response.raise_for_status()
                data = response.json()

            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            description = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            city = data["name"]
            country = data["sys"]["country"]

            output = (
                f"Weather in {city}, {country}:\n"
                f"  {description.capitalize()}\n"
                f"  Temperature: {temp}C (feels like {feels_like}C)\n"
                f"  Humidity: {humidity}%"
            )

            return PluginResult(
                status=PluginResultStatus.SUCCESS,
                output=output,
                data={
                    "city": city,
                    "country": country,
                    "temp": temp,
                    "feels_like": feels_like,
                    "description": description,
                    "humidity": humidity,
                },
            )

        except httpx.HTTPError as e:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Weather API error: {e}",
            )
