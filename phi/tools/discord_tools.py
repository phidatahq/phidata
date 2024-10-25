"""Discord integration tools."""

import json
from os import getenv
from typing import Union, Optional
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import discord
    from discord.ext import commands
except ImportError:
    raise ImportError("`discord` package not installed. Please install using `pip install discord.py`")

MessageableChannel = Union[discord.TextChannel, discord.Thread, discord.DMChannel]


class DiscordTools(Toolkit):
    def __init__(
        self,
        bot_token: Optional[str] = None,
        enable_messaging: bool = True,
        enable_history: bool = True,
        enable_channel_management: bool = True,
    ):
        """Initialize Discord tools.

        Args:
            bot_token: Discord bot token for authentication. If not provided, will try to get from DISCORD_BOT_TOKEN env var
            enable_messaging: Whether to enable message sending functionality
            enable_history: Whether to enable message history retrieval
            enable_channel_management: Whether to enable channel management
        """
        super().__init__(name="discord_tools")

        self.bot_token = bot_token or getenv("DISCORD_BOT_TOKEN")
        if not self.bot_token:
            logger.error("DISCORD_BOT_TOKEN not set. Please set the DISCORD_BOT_TOKEN environment variable.")

        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        if enable_messaging:
            self.register(self.send_message)
            self.register(self.delete_message)
        if enable_history:
            self.register(self.get_channel_messages)
        if enable_channel_management:
            self.register(self.list_channels)
            self.register(self.get_channel_info)

    async def send_message(self, channel_id: int, message: str) -> str:
        """Send a message to a specific Discord channel.

        Args:
            channel_id: The ID of the Discord channel
            message: The message to send

        Returns:
            str: Success or error message
        """
        try:
            channel = await self.bot.fetch_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
                await channel.send(message)
                return "Message sent successfully"
            return "This channel type doesn't support sending messages"
        except discord.errors.NotFound:
            return f"Channel {channel_id} not found"
        except discord.errors.Forbidden:
            return "Bot doesn't have permission to send messages"
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return f"Error sending Discord message: {e}"

    async def delete_message(self, channel_id: int, message_id: int) -> str:
        """Delete a message.

        Args:
            channel_id: The ID of the Discord channel
            message_id: The ID of the message to delete

        Returns:
            str: Success or error message
        """
        try:
            channel = await self.bot.fetch_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
                message = await channel.fetch_message(message_id)
                await message.delete()
                return "Message deleted successfully"
            return "This channel type doesn't support message deletion"
        except discord.errors.NotFound:
            return "Message or channel not found"
        except discord.errors.Forbidden:
            return "Bot doesn't have permission to delete messages"
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return f"Error deleting message: {e}"

    async def get_channel_messages(self, channel_id: int, limit: int = 100) -> str:
        """Get recent messages from a Discord channel.

        Args:
            channel_id: The ID of the Discord channel
            limit: Maximum number of messages to retrieve

        Returns:
            str: JSON string containing messages or error message
        """
        try:
            channel = await self.bot.fetch_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
                messages = []
                async for message in channel.history(limit=limit):
                    messages.append(
                        {
                            "id": str(message.id),
                            "content": message.content,
                            "author": str(message.author),
                            "timestamp": str(message.created_at),
                        }
                    )
                return json.dumps(messages, indent=4)
            return "This channel type doesn't support message history"
        except discord.errors.NotFound:
            return f"Channel {channel_id} not found"
        except discord.errors.Forbidden:
            return "Bot doesn't have permission to read messages"
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return f"Error getting messages: {e}"

    async def list_channels(self, guild_id: int) -> str:
        """List all channels in a Discord server.

        Args:
            guild_id: The ID of the Discord server

        Returns:
            str: JSON string containing list of channels
        """
        try:
            guild = await self.bot.fetch_guild(guild_id)
            channels = await guild.fetch_channels()
            channel_list = [
                {"id": str(channel.id), "name": channel.name, "type": str(channel.type)} for channel in channels
            ]
            return json.dumps(channel_list, indent=4)
        except discord.errors.NotFound:
            return f"Server {guild_id} not found"
        except discord.errors.Forbidden:
            return "Bot doesn't have permission to view channels"
        except Exception as e:
            logger.error(f"Error listing channels: {e}")
            return f"Error listing channels: {e}"

    async def get_channel_info(self, channel_id: int) -> str:
        """Get information about a specific channel.

        Args:
            channel_id: The ID of the Discord channel

        Returns:
            str: JSON string containing channel information
        """
        try:
            channel = await self.bot.fetch_channel(channel_id)
            channel_info = {"id": str(channel.id), "type": str(getattr(channel, "type", "unknown"))}

            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
                channel_info.update(
                    {"name": channel.name, "position": str(channel.position), "created_at": str(channel.created_at)}
                )

            return json.dumps(channel_info, indent=4)
        except discord.errors.NotFound:
            return f"Channel {channel_id} not found"
        except discord.errors.Forbidden:
            return "Bot doesn't have permission to view this channel"
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return f"Error getting channel info: {e}"


def get_tool_name() -> str:
    """Get the name of the tool."""
    return "discord"


def get_tool_description() -> str:
    """Get the description of the tool."""
    return "Tool for interacting with Discord channels and servers"


def get_tool_config() -> dict:
    """Get the required configuration for the tool."""
    return {"bot_token": {"type": "string", "description": "Discord bot token for authentication", "required": True}}
