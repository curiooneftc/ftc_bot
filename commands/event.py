import discord
from discord import app_commands
import requests
from helpers import std_vars, assign_places

query = std_vars.SCOUT_QUERY
tpp = std_vars.TEAMS_PER_PAGE

from API.first import build_auth_header, get_current_season
from conf import BASE_URL, BASE_URL_SCOUT

def build_embeds(event_name: str, teams: list[dict], sort_mode: str) -> list[discord.Embed]:
    embeds = []

    for page_index in range(0, len(teams), tpp):
        chunk = teams[page_index:page_index + tpp]

        embed = discord.Embed(
            title=event_name,
            description=f"**Team Rankings — {sort_mode}**",
            color=discord.Color.blurple()
        )

        for t in chunk:
            embed.add_field(
                name=f"#{t['pos']} — Team {t['team']}",
                value=(
                    f"**{t['name']}**\n"
                    f"Avg: {t['avg']} | NP: {t['avgNp']} | "
                    f"W-L: {t['wins']}-{t['losses']}"
                ),
                inline=False
            )

        embed.set_footer(
            text=f"Page {len(embeds) + 1} / {((len(teams) - 1) // tpp) + 1}"
        )
        embeds.append(embed)

    return embeds

class RankingView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, event_name: str, teams: list[dict]):
        super().__init__(timeout=180)
        self.author_id = interaction.user.id
        self.event_name = event_name
        self.original_teams = teams
        self.page = 0
        self.sort_mode = "Rank"
        self.embeds = self._rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _rebuild(self):
        teams = self.original_teams.copy()

        if self.sort_mode == "Rank":
            teams.sort(key=lambda x: (x["rank"] is None, x["rank"] or 9999))
            for t in teams:
                t["pos"] = t["rank"]

        elif self.sort_mode == "Avg":
            teams.sort(key=lambda x: (x["_avg_raw"] is None, -(x["_avg_raw"] or 0)))
            assign_places(teams, "_avg_raw")
            for t in teams:
                t["pos"] = t["place"]

        elif self.sort_mode == "Avg NP":
            teams.sort(key=lambda x: (x["_avg_rawNp"] is None, -(x["_avg_rawNp"] or 0)))
            assign_places(teams, "_avg_rawNp")
            for t in teams:
                t["pos"] = t["place"]

        return build_embeds(self.event_name, teams, self.sort_mode)

    async def _update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=self.embeds[self.page],
            view=self
        )

    # Pagination
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, _):
        if self.page > 0:
            self.page -= 1
        await self._update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _):
        if self.page < len(self.embeds) - 1:
            self.page += 1
        await self._update(interaction)

    # Sorting
    @discord.ui.button(label="🏆 Rank", style=discord.ButtonStyle.primary)
    async def sort_rank(self, interaction: discord.Interaction, _):
        self.sort_mode = "Rank"
        self.page = 0
        self.embeds = self._rebuild()
        await self._update(interaction)

    @discord.ui.button(label="📊 Avg", style=discord.ButtonStyle.primary)
    async def sort_avg(self, interaction: discord.Interaction, _):
        self.sort_mode = "Avg"
        self.page = 0
        self.embeds = self._rebuild()
        await self._update(interaction)

    @discord.ui.button(label="⚡ Avg NP", style=discord.ButtonStyle.primary)
    async def sort_np(self, interaction: discord.Interaction, _):
        self.sort_mode = "Avg NP"
        self.page = 0
        self.embeds = self._rebuild()
        await self._update(interaction)

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
        season = season or current_season

        r = requests.get(f"{BASE_URL}/{season}/events", headers=headers, timeout=10)
        if r.status_code != 200:
            await interaction.followup.send("Failed to fetch events.")
            return

        event = next(
            (e for e in r.json().get("events", [])
             if e.get("code", "").lower() == event_code.lower()),
            None
        )

        if not event:
            await interaction.followup.send("Event not found.")
            return

        info_embed = discord.Embed(
            title=event["name"],
            description=(
                f"Code: `{event['code']}`\n"
                f"{event['venue']}, {event['city']} {event['stateprov']}\n"
                f"[Website]({event['website']})"
            ),
            color=discord.Color.green()
        )

        await interaction.followup.send(embed=info_embed)

        if not advanced:
            return

        response = requests.post(
            BASE_URL_SCOUT,
            json={"query": query, "variables": {"season": season, "code": event["code"].upper()}},
            timeout=10
        )

        scout_event = response.json().get("data", {}).get("eventByCode")
        if not scout_event or not scout_event.get("teams"):
            await interaction.followup.send("No team data available yet.")
            return

        team_rows = []
        for t in scout_event["teams"]:
            stats = t.get("stats") or {}
            team = t.get("team") or {}

            avg = stats.get("avg", {}).get("totalPoints")
            avgNp = stats.get("avg", {}).get("totalPointsNp")

            team_rows.append({
                "team": t["teamNumber"],
                "name": team.get("name", "Unknown"),
                "rank": stats.get("rank"),
                "avg": round(avg, 1) if avg is not None else "—",
                "avgNp": round(avgNp, 1) if avgNp is not None else "—",
                "wins": stats.get("wins", "—"),
                "losses": stats.get("losses", "—"),
                "_avg_raw": avg,
                "_avg_rawNp": avgNp,
            })

        view = RankingView(interaction, event["name"], team_rows)
        await interaction.followup.send(embed=view.embeds[0], view=view)
