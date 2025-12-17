import discord
from discord import app_commands
from conf import DISCORD_TOKEN
from commands import all_commands

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        for command_class in all_commands:
            command_instance = command_class()
            self.tree.add_command(command_instance)
        await self.tree.sync()
        print("Slash commands synced")

client = MyClient()
client.run(DISCORD_TOKEN)
