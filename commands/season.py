import discord
from discord import app_commands
import requests

from API.first import build_auth_header, get_current_season
from conf import BASE_URL

class SeasonCommand(app_commands.Command):
    def __init__(self):
        super().__init__(
            name="season",
            description="Get FTC season info",
            callback=self.season
        )

    async def season(
        self,
        interaction: discord.Interaction,
        year: int | None = None
    ):
        await interaction.response.defer()

        headers = build_auth_header()
        current_season = get_current_season()

        if year is not None and year > current_season:
            await interaction.followup.send("Are you from the future?")
            return

        try:
            if year is None:
                year = current_season

            r = requests.get(
                f"{BASE_URL}/{year}",
                headers=headers,
                timeout=10
            )

            if r.status_code == 401:
                await interaction.followup.send("Unauthorized – check API credentials.")
                return

            if r.status_code == 400:
                await interaction.followup.send(f"Couldn't find season {year}")
                return

            if r.status_code == 501:
                await interaction.followup.send(f"You went back to far in time since before ftc")
                return

            if r.status_code != 200:
                await interaction.followup.send(f"FIRST API error `{r.status_code}`.")
                return

            data = r.json()

            await interaction.followup.send(
                f"**Season {year}**\n"
                f"Game: {data['gameName']}\n"
                f"Kickoff Date: {data.get('kickoff', 'N/A')}\n"
                f"Events: {data.get('eventCount', 'N/A')}\n"
                f"Teams: {data.get('teamCount', 'N/A')}"
            )

        except requests.exceptions.Timeout:
            await interaction.followup.send("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"Network error: {str(e)}")
        except KeyError as e:
            await interaction.followup.send(f"Unexpected API response format: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")