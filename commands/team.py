import discord
from discord import app_commands
import requests

from API.first import build_auth_header, get_current_season
from conf import BASE_URL

class TeamCommand(app_commands.Command):
    def __init__(self):
        super().__init__(
            name="team",
            description="Get FTC team info",
            callback=self.team
        )

    async def team(
        self,
        interaction: discord.Interaction,
        team_number: int,
        season: int | None = None
    ):
        await interaction.response.defer()

        headers = build_auth_header()
        current_season = get_current_season()

        if season is not None and season > current_season:
            await interaction.followup.send("Are you from the future?")
            return

        try:
            if season is None:
                season = current_season

            r = requests.get(
                f"{BASE_URL}/{season}/teams",
                params={"teamNumber": team_number},
                headers=headers,
                timeout=10
            )

            if r.status_code == 401:
                await interaction.followup.send("Unauthorized – check API credentials.")
                return

            if r.status_code == 400:
                await interaction.followup.send(f"Couldn't find that team number in season {season}")
                return

            if r.status_code != 200:
                await interaction.followup.send(f"FIRST API error `{r.status_code}`.")
                return

            data = r.json()

            if not data.get("teams"):
                await interaction.followup.send("Team not found.")
                return

            team = data["teams"][0]

            await interaction.followup.send(
                f"**{team['nameShort']}** (Season {season})\n"
                f"Team #{team['teamNumber']}\n"
                f"Location: {team.get('city', 'Unknown')}, {team.get('stateProv', '')}\n"
                f"Rookie Year: {team.get('rookieYear', 'Unknown')}"
            )

        except requests.exceptions.Timeout:
            await interaction.followup.send("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"Network error: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")