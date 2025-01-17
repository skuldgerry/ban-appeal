import os
import discord
import json
import re
import logging
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified format
)
logger = logging.getLogger('discord')

# Helper functions
def load_config(guild_id, config_type):
    config_path = f'config/{guild_id}/{config_type}.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            return json.load(file)
    return {}

def save_config(guild_id, config_type, config):
    config_path = f'config/{guild_id}/{config_type}.json'
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

def is_valid_steam_id(steam_id):
    steam_id64_pattern = re.compile(r'^7656\d{13}$')
    return steam_id64_pattern.match(steam_id)

def initialize_config(guild_id):
    format_config = {
        "ban_appeal_channel_id": None,
        "whitelisted_roles": [],
        "message_format": "AC Driver Name:\nSteam ID:\nDetails:"
    }
    error_config = {
        "error_message": (
            "To use line breaks in Discord, use Shift + Enter.\n"
            "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
            "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
        ),
        "steam_id_error_message": (
            "Your Steam ID is not valid. Please provide a valid SteamID64 (a 17-digit number starting with '7656').\n"
            "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
            "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
        )
    }
    logs_config = {
        "log_channel_id": None
    }
    
    # Load existing configs if they exist
    existing_format = load_config(guild_id, 'format')
    existing_error = load_config(guild_id, 'error')
    existing_logs = load_config(guild_id, 'logs')
    
    # Merge existing configs with new defaults, without modifying existing ones
    if existing_format:
        save_config(guild_id, 'format', existing_format)
    else:
        save_config(guild_id, 'format', format_config)
        
    if existing_error:
        save_config(guild_id, 'error', existing_error)
    else:
        save_config(guild_id, 'error', error_config)
        
    if existing_logs:
        save_config(guild_id, 'logs', existing_logs)
    else:
        save_config(guild_id, 'logs', logs_config)

class CustomBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing bot...")
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents
        )
        self.reconnect_attempts = 0
        self.tree.on_error = self.on_app_command_error
        logger.info("Bot initialized successfully")

    async def setup_hook(self):
        logger.info("Setting up bot...")
        try:
            await self.tree.sync()
            logger.info("Command tree synced successfully")
        except Exception as e:
            logger.error(f"Error syncing command tree: {e}")
            raise
        
    async def on_ready(self):
        try:
            logger.info("Bot on_ready event triggered")
            self.reconnect_attempts = 0
            logger.info(f'Logged in as {self.user}')
            
            # Print invite link
            logger.info("Generating invite link...")
            app_info = await self.application_info()
            permissions = discord.Permissions(
                manage_messages=True,
                read_messages=True,
                send_messages=True,
                manage_roles=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                add_reactions=True
            )
            invite_link = discord.utils.oauth_url(
                app_info.id,
                permissions=permissions,
                scopes=("bot", "applications.commands")
            )
            
            # Force print to console
            with open('/dev/stdout', 'w') as console:
                console.write("\n" + "="*50 + "\n")
                console.write("Bot is ready!\n")
                console.write("-"*50 + "\n")
                console.write(f"Bot Name: {self.user}\n")
                console.write(f"Bot ID: {self.user.id}\n")
                console.write("-"*50 + "\n")
                console.write("Invite Link:\n")
                console.write(f"{invite_link}\n")
                console.write("-"*50 + "\n")
                console.write(f"Required Permissions: {permissions.value}\n")
                console.write("="*50 + "\n\n")
                console.flush()
            
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")
            raise

    async def on_disconnect(self):
        self.reconnect_attempts += 1
        wait_time = min(2 ** self.reconnect_attempts, 60)
        logger.warning(f'Disconnected from Discord. Attempting to reconnect in {wait_time} seconds...')
        await asyncio.sleep(wait_time)

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        try:
            if isinstance(error, app_commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                    ephemeral=True
                )
            elif isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "You don't have the required permissions to use this command.",
                    ephemeral=True
                )
            else:
                logger.error(f"Error in command {interaction.command}: {error}")
                await interaction.response.send_message(
                    "An error occurred while processing the command.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error handling command error: {e}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if message is in ban appeal channel
        config = load_config(message.guild.id, 'format')
        if message.channel.id != config.get('ban_appeal_channel_id'):
            return

        # Check if user has whitelisted role
        user_roles = [role.id for role in message.author.roles]
        if not any(role_id in config.get('whitelisted_roles', []) for role_id in user_roles):
            # Verify format
            expected_format = config.get('message_format', "AC Driver Name:\nSteam ID:\nDetails:")
            format_sections = expected_format.split('\n')
            message_content = message.content.strip()
            
            # Check if message follows format
            format_valid = True
            steam_id = None
            
            try:
                lines = message_content.split('\n')
                if len(lines) < len(format_sections):
                    format_valid = False
                else:
                    for i, section in enumerate(format_sections):
                        if not lines[i].startswith(section.split(':')[0]):
                            format_valid = False
                            break
                        if 'Steam ID' in section:
                            steam_id = lines[i].split(':', 1)[1].strip()
            except:
                format_valid = False

            if not format_valid:
                error_config = load_config(message.guild.id, 'error')
                error_msg = (
                    f"Hi {message.author.mention}, your ban appeal format is incorrect. "
                    f"Please use the following format:\n```\n{expected_format}```\n"
                    f"{error_config.get('error_message', '')}"
                )
                
                # Log the deletion
                logs_config = load_config(message.guild.id, 'logs')
                if logs_config.get('log_channel_id'):
                    log_channel = message.guild.get_channel(logs_config['log_channel_id'])
                    if log_channel:
                        await log_channel.send(
                            f"Deleted message from {message.author.mention} for incorrect format.\n"
                            f"Message content: {message_content}"
                        )
                
                await message.delete()
                await message.author.send(error_msg)
                return

            # Verify Steam ID if format is valid
            if steam_id and not is_valid_steam_id(steam_id):
                error_config = load_config(message.guild.id, 'error')
                
                # Log the deletion
                logs_config = load_config(message.guild.id, 'logs')
                if logs_config.get('log_channel_id'):
                    log_channel = message.guild.get_channel(logs_config['log_channel_id'])
                    if log_channel:
                        await log_channel.send(
                            f"Deleted message from {message.author.mention} for invalid Steam ID.\n"
                            f"Message content: {message_content}"
                        )
                
                await message.delete()
                await message.author.send(error_config.get('steam_id_error_message', ''))
                return

class ChannelSelectView(discord.ui.View):
    def __init__(self, parent_view, channel_type: str):
        super().__init__()
        self.parent_view = parent_view
        self.channel_type = channel_type
        self.selected_channel = None

        # Add channel select
        self.channel_select = discord.ui.ChannelSelect(
            placeholder="Select a channel",
            channel_types=[discord.ChannelType.text]
        )
        self.channel_select.callback = self.channel_select_callback
        self.add_item(self.channel_select)

        # Add confirm button after channel select
        self.confirm_button = discord.ui.Button(
            label="Confirm",
            style=discord.ButtonStyle.primary,
            row=1  # Put button in the next row
        )
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

    async def channel_select_callback(self, interaction: discord.Interaction):
        self.selected_channel = self.channel_select.values[0]
        await interaction.response.defer()

    async def confirm_callback(self, interaction: discord.Interaction):
        if not self.selected_channel:
            await interaction.response.send_message("Please select a channel first!", ephemeral=True)
            return

        if self.channel_type == "ban_appeal":
            config = load_config(interaction.guild.id, 'format')
            config['ban_appeal_channel_id'] = self.selected_channel.id
            save_config(interaction.guild.id, 'format', config)
            await self.parent_view.show_format_setup(interaction)
        else:
            config = load_config(interaction.guild.id, 'logs')
            config['log_channel_id'] = self.selected_channel.id
            save_config(interaction.guild.id, 'logs', config)
            await interaction.response.send_message("✅ Setup complete!", ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.selected_roles = []

        # Add role select
        self.role_select = discord.ui.RoleSelect(
            placeholder="Select roles to whitelist",
            min_values=1,
            max_values=25
        )
        self.role_select.callback = self.role_select_callback
        self.add_item(self.role_select)

        # Add confirm button after role select
        self.confirm_button = discord.ui.Button(
            label="Confirm",
            style=discord.ButtonStyle.primary,
            row=1  # Put button in the next row
        )
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

    async def role_select_callback(self, interaction: discord.Interaction):
        self.selected_roles = self.role_select.values
        await interaction.response.defer()

    async def confirm_callback(self, interaction: discord.Interaction):
        if not self.selected_roles:
            await interaction.response.send_message("Please select at least one role!", ephemeral=True)
            return

        config = load_config(interaction.guild.id, 'format')
        if 'whitelisted_roles' not in config:
            config['whitelisted_roles'] = []
        
        for role in self.selected_roles:
            if role.id not in config['whitelisted_roles']:
                config['whitelisted_roles'].append(role.id)
        
        save_config(interaction.guild.id, 'format', config)
        await self.parent_view.show_error_message_setup(interaction)

class ErrorMessageSetupView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    @discord.ui.button(label="Accept Default", style=discord.ButtonStyle.primary)
    async def accept_default(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(interaction.guild.id, 'error')
        config['error_message'] = (
            "To use line breaks in Discord, use Shift + Enter.\n"
            "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
            "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
        )
        config['steam_id_error_message'] = (
            "Your Steam ID is not valid. Please provide a valid SteamID64 (a 17-digit number starting with '7656').\n"
            "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
            "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
        )
        save_config(interaction.guild.id, 'error', config)
        await self.parent_view.show_channel_select(interaction, "logs")

    @discord.ui.button(label="Customize", style=discord.ButtonStyle.secondary)
    async def customize(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomErrorMessageModal(self.parent_view))

class CustomErrorMessageModal(discord.ui.Modal):
    def __init__(self, parent_view):
        super().__init__(title="Customize Error Message")
        self.parent_view = parent_view
        self.error_input = discord.ui.TextInput(
            label="Error Message",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your custom error message",
            default=(
                "To use line breaks in Discord, use Shift + Enter.\n"
                "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
                "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
            ),
            required=True
        )
        self.add_item(self.error_input)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config(interaction.guild.id, 'error')
        config['error_message'] = self.error_input.value
        save_config(interaction.guild.id, 'error', config)
        await self.parent_view.show_channel_select(interaction, "logs")

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.current_step = 0
        # Initialize default configs
        self.format_config = {
            "ban_appeal_channel_id": None,
            "whitelisted_roles": [],
            "message_format": "AC Driver Name:\nSteam ID:\nDetails:"
        }
        self.error_config = {
            "error_message": (
                "To use line breaks in Discord, use Shift + Enter.\n"
                "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
                "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
            ),
            "steam_id_error_message": (
                "Your Steam ID is not valid. Please provide a valid SteamID64 (a 17-digit number starting with '7656').\n"
                "You can find your Steam ID at https://steamidfinder.com/ (provide SteamID64 (Dec)) or in the Content Manager. "
                "Go to Settings > Content Manager > General, and then in front of Steam Profile, you should be able to get your Steam ID."
            )
        }
        self.logs_config = {
            "log_channel_id": None
        }

    @discord.ui.button(label="Start Setup", style=discord.ButtonStyle.primary)
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_channel_select(interaction, "ban_appeal")

    async def show_channel_select(self, interaction: discord.Interaction, channel_type: str):
        view = ChannelSelectView(self, channel_type)
        title = "Ban Appeal Channel" if channel_type == "ban_appeal" else "Logs Channel"
        await interaction.response.edit_message(
            content=f"Please select the {title}:",
            view=view,
            embed=None
        )

    async def show_format_setup(self, interaction: discord.Interaction):
        default_format = "AC Driver Name:\nSteam ID:\nDetails:"
        embed = discord.Embed(
            title="Message Format Setup",
            description=f"Default format:\n```\n{default_format}\n```\nWould you like to use this format or customize it?",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Note",
            value="Users can use line breaks in the Details section.",
            inline=False
        )
        view = FormatView(self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def show_error_message_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Error Message Setup",
            description=f"Default error message:\n```\n{self.error_config['error_message']}\n```\nWould you like to use this message or customize it?",
            color=discord.Color.blue()
        )
        view = ErrorMessageSetupView(self)
        await interaction.response.edit_message(embed=embed, view=view)

class FormatView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    @discord.ui.button(label="Accept Default", style=discord.ButtonStyle.primary)
    async def accept_default(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(interaction.guild.id, 'format')
        config['message_format'] = "AC Driver Name:\nSteam ID:\nDetails:"
        save_config(interaction.guild.id, 'format', config)
        await self.show_role_setup(interaction)

    @discord.ui.button(label="Customize", style=discord.ButtonStyle.secondary)
    async def customize(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomFormatModal(self))

    async def show_role_setup(self, interaction: discord.Interaction):
        view = RoleSelectView(self.parent_view)
        await interaction.response.edit_message(
            content="Please select the roles to whitelist:",
            view=view,
            embed=None
        )

class CustomFormatModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Customize Format")
        self.view = view
        self.format_input = discord.ui.TextInput(
            label="Message Format",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your custom format",
            default="AC Driver Name:\nSteam ID:\nDetails:",
            required=True
        )
        self.add_item(self.format_input)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config(interaction.guild.id, 'format')
        config['message_format'] = self.format_input.value
        save_config(interaction.guild.id, 'format', config)
        await self.view.show_role_setup(interaction)

# Create the bot instance first
logger.info("Starting bot initialization...")
try:
    bot = CustomBot()
except Exception as e:
    logger.error(f"Error creating bot instance: {e}")
    raise

# Now define the commands
@bot.tree.command(name="setup", description="Start the bot setup process")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    """Start the bot setup process"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="Ban Appeal Bot Setup",
        description="Welcome to the setup wizard! Click 'Start Setup' to begin.",
        color=discord.Color.blue()
    )
    
    view = SetupView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="add_roles", description="Add roles to the whitelist")
@app_commands.default_permissions(administrator=True)
async def add_roles(interaction: discord.Interaction, roles: str):
    """Add roles to the whitelist. Separate multiple role IDs with spaces."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return
        
    role_ids = roles.split()
    config = load_config(interaction.guild.id, 'format')
    
    if 'whitelisted_roles' not in config:
        config['whitelisted_roles'] = []
    
    added_roles = []
    already_whitelisted = []
    invalid_roles = []
    
    for role_id in role_ids:
        try:
            role = interaction.guild.get_role(int(role_id))
            if role:
                if role.id not in config['whitelisted_roles']:
                    config['whitelisted_roles'].append(role.id)
                    added_roles.append(role.name)
                else:
                    already_whitelisted.append(role.name)
            else:
                invalid_roles.append(role_id)
        except ValueError:
            invalid_roles.append(role_id)
    
    save_config(interaction.guild.id, 'format', config)
    
    response = []
    if added_roles:
        response.append(f"✅ Added roles: {', '.join(added_roles)}")
    if already_whitelisted:
        response.append(f"ℹ️ Already whitelisted: {', '.join(already_whitelisted)}")
    if invalid_roles:
        response.append(f"❌ Invalid role IDs: {', '.join(invalid_roles)}")
    
    await interaction.response.send_message("\n".join(response), ephemeral=True)

@bot.tree.command(name="remove_roles", description="Remove roles from the whitelist")
@app_commands.default_permissions(administrator=True)
async def remove_roles(interaction: discord.Interaction, roles: str):
    """Remove roles from the whitelist. Separate multiple role IDs with spaces."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return
        
    role_ids = roles.split()
    config = load_config(interaction.guild.id, 'format')
    
    if 'whitelisted_roles' not in config:
        config['whitelisted_roles'] = []
    
    removed_roles = []
    not_whitelisted = []
    invalid_roles = []
    
    for role_id in role_ids:
        try:
            role_id = int(role_id)
            role = interaction.guild.get_role(role_id)
            if role:
                if role_id in config['whitelisted_roles']:
                    config['whitelisted_roles'].remove(role_id)
                    removed_roles.append(role.name)
                else:
                    not_whitelisted.append(role.name)
            else:
                invalid_roles.append(str(role_id))
        except ValueError:
            invalid_roles.append(role_id)
    
    save_config(interaction.guild.id, 'format', config)
    
    response = []
    if removed_roles:
        response.append(f"✅ Removed roles: {', '.join(removed_roles)}")
    if not_whitelisted:
        response.append(f"ℹ️ Not in whitelist: {', '.join(not_whitelisted)}")
    if invalid_roles:
        response.append(f"❌ Invalid role IDs: {', '.join(invalid_roles)}")
    
    await interaction.response.send_message("\n".join(response), ephemeral=True)

# Run the bot last
logger.info("Running bot...")
try:
    bot.run(TOKEN)
except Exception as e:
    logger.error(f"Fatal error: {e}")
    raise
