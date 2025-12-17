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
    teams {
      teamNumber
      stats {
        ... on TeamEventStats2025 {
          rank
          avg {
            totalPoints
            totalPointsNp
          }
          rp
          wins
          losses
        }
      }
      team {
        name
      }
    }
  }
}
"""

def assign_places(rows, value_key):
    place = 0
    last_value = None
    for i, row in enumerate(rows):
        value = row[value_key]
        if value != last_value:
            place = i + 1
            last_value = value
        row["place"] = place


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
        rank_by_points: bool | None = False,
        rank_by_points_np: bool | None = False
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

            if rank_by_points and not advanced:
                await interaction.followup.send(
                    "You can only see this data with advanced."
                )
                return

            if rank_by_points_np and not advanced:
                await interaction.followup.send(
                    "You can only see this data with advanced."
                )
                return

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

                teams = scout_event.get("teams", [])

                if not teams:
                    message += "\nNo team ranking data available yet."
                else:
                    team_rows = []

                    for t in teams:
                        stats = t.get("stats") or {}
                        team_self = t.get("team") or {}

                        rank = stats.get("rank")
                        avg = stats.get("avg", {}).get("totalPoints")
                        avgNp = stats.get("avg", {}).get("totalPointsNp")
                        wins = stats.get("wins")
                        losses = stats.get("losses")
                        name = team_self.get("name")

                        if avg is None and rank is None:
                            continue

                        team_rows.append({
                            "team": t["teamNumber"],
                            "name": name,
                            "rank": rank,
                            "avg": round(avg, 1) if avg is not None else "—",
                            "avgNp": round(avgNp, 1) if avg is not None else "—",
                            "wins": wins if wins is not None else "—",
                            "losses": losses if losses is not None else "—",
                            "_avg_raw": avg,
                            "_avg_rawNp": avgNp,
                        })

                    if rank_by_points and rank_by_points_np:
                        await interaction.followup.send(
                            "Choose only one: rank_by_points OR rank_by_points_np."
                        )
                        return


                    if rank_by_points:
                        team_rows.sort(
                            key=lambda x: (x["_avg_raw"] is None, -(x["_avg_raw"] or 0))
                        )
                        assign_places(team_rows, "_avg_raw")
                        message += "\n**Team Rankings (by Avg Points)**\n"
                        show_place = True

                    elif rank_by_points_np:
                        team_rows.sort(
                            key=lambda x: (x["_avg_rawNp"] is None, -(x["_avg_rawNp"] or 0))
                        )
                        assign_places(team_rows, "_avg_rawNp")
                        message += "\n**Team Rankings (by Avg Points Np)**\n"
                        show_place = True

                    else:
                        team_rows.sort(
                            key=lambda x: (x["rank"] is None, x["rank"] or 9999)
                        )
                        message += "\n**Team Rankings (by Official Rank)**\n"
                        show_place = False

                    for t in team_rows:
                        pos = t["place"] if show_place else t["rank"]

                        message += (
                            f"#{pos} — Team {t['team']}, **{t['name']}** | "
                            f"Avg: {t['avg']} | "
                            f"NP: {t['avgNp']} | "
                            f"W-L: {t['wins']}-{t['losses']}\n"
                        )

            await interaction.followup.send(message[:2000])

        except requests.exceptions.Timeout:
            await interaction.followup.send("Request timed out.")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")
