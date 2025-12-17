import discord
from discord import app_commands
import requests

from API.first import build_auth_header, get_current_season
from conf import BASE_URL, BASE_URL_SCOUT

SCOUT_QUERY = """
query EventByCode($season: Int!, $code: String!) {
  eventByCode(season: $season, code: $code) {
    name
    code
    finished
    fieldCount
    ongoing
    started
    matches {
      matchNum
      teams {
        alliance
        teamNumber
        team {
          name
        }
      }
      scheduledStartTime
      postResultTime
      scores {
        ... on MatchScores2025 {
          red {
            totalPoints
            totalPointsNp
          }
          blue {
            totalPoints
            totalPointsNp
          }
        }
      }
    }
  }
}
"""

class EventCommand(app_commands.Command):
    def __init__(self):
        super().__init__(
            name="event",
            description="Get FTC event info",
            callback=self.event
        )

    async def event(
        self,
        interaction: discord.Interaction,
        event_code: str,
        season: int | None = None,
        advanced: bool | None = False,
    ):
        await interaction.response.defer()

        headers = build_auth_header()
        current_season = get_current_season()

        if season is None:
            season = current_season

        if season > current_season:
            await interaction.followup.send("Are you from the future?")
            return

        try:
            r = requests.get(
                f"{BASE_URL}/{season}/events",
                headers=headers,
                timeout=10
            )

            if r.status_code == 401:
                await interaction.followup.send("Unauthorized – check API credentials.")
                return

            if r.status_code != 200:
                await interaction.followup.send(f"FIRST API error `{r.status_code}`.")
                return

            data = r.json()

            event = next(
                (e for e in data.get("events", [])
                 if e.get("code", "").lower() == event_code.lower()),
                None
            )

            if not event:
                await interaction.followup.send("Event not found.")
                return

            message = (
                f"**{event['name']}**\n"
                f"Code: `{event['code']}`\n"
                f"Type: {event['typeName']}\n"
                f"{event['venue']}, {event['address']}\n"
                f"{event['city']}, {event['stateprov']}\n"
                f"Website: {event['website']}\n"
            )

            if event.get("liveStreamUrl"):
                message += f"Livestream: {event['liveStreamUrl']}\n"

            if advanced:
                variables = {
                    "season": season,
                    "code": event["code"].upper()
                }

                response = requests.post(
                    BASE_URL_SCOUT,
                    json={"query": SCOUT_QUERY, "variables": variables},
                    timeout=10
                )

                scout_data = response.json()

                if "errors" in scout_data:
                    await interaction.followup.send(
                        f"FTC Scout error: {scout_data['errors'][0]['message']}"
                    )
                    return

                scout_event = scout_data.get("data", {}).get("eventByCode")

                if not scout_event:
                    await interaction.followup.send(
                        "FTC Scout has no data for this event yet."
                    )
                    return

                message += (
                    f"\n**FTC Scout Status**\n"
                    f"Started: {scout_event['started']}\n"
                    f"Ongoing: {scout_event['ongoing']}\n"
                    f"Finished: {scout_event['finished']}\n"
                    f"Fields: {scout_event['fieldCount']}\n"
                )

                matches = scout_event.get("matches", [])

                if not matches:
                    message += "\nNo match data available yet."
                else:
                    message += "\n**Matches**\n"

                    for m in matches:
                        scores = m.get("scores")
                        teams = m.get("teams", [])

                        red_teams = []
                        blue_teams = []

                        for team in teams:
                            alliance = team.get("alliance", "").lower()
                            team_number = team.get("teamNumber")

                            label = f"{team_number}"

                            if alliance == "red":
                                red_teams.append(label)
                            elif alliance == "blue":
                                blue_teams.append(label)

                        red_score = scores["red"]["totalPoints"] if scores else "—"
                        blue_score = scores["blue"]["totalPoints"] if scores else "—"

                        message += (
                            f"Match {m['matchNum']} — "
                            f"Red ({', '.join(red_teams)}): {red_score} | "
                            f"Blue ({', '.join(blue_teams)}): {blue_score}\n"
                        )

            await interaction.followup.send(message[:2000])

        except requests.exceptions.Timeout:
            await interaction.followup.send("Request timed out.")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")
