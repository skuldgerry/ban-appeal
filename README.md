# Discord Ban Appeal Bot

A Discord bot that manages ban appeal channels by enforcing specific formats and validating Steam IDs, with whitelist capabilities and customizable messages.

## Features

- Automatically deletes messages that don't follow the specified format
- Steam ID validation
- Whitelist system to exempt specific roles
- Customizable error messages
- Logging system for deleted messages
- Modern Discord UI with slash commands
- Administrator-only controls

## Commands

All commands require administrator permissions:

- `/settings` - Opens the settings menu with UI buttons
- `/add_roles <role_ids>` - Add roles to the whitelist
- `/remove_roles <role_ids>` - Remove roles from the whitelist

## Docker Setup

The bot is available on Docker Hub:

```bash
docker pull skuldgerry/ban-appeal-bot:2.5.0
```

```yaml
version: '3'
services:
  discord-bot:
    image: skuldgerry/ban-appeal-bot:2.5.0
    container_name: BAN-APPEAL-BOT
    environment:
      BOT_TOKEN: your_bot_token_here
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

After starting the container, check the console logs for the bot's invite link. You can use this link to invite the bot to your server with all required permissions.

### Required Permissions

The bot requires the following permissions:
- Administrator (for command access)
- View Channels
- Send Messages
- Manage Messages
- Manage Roles
- Read Message History
- Create Public Threads
- Send Messages in Threads
- Manage Threads

## Setup

1. Create a Discord application and bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Get your bot token
3. Deploy using Docker:
   - Create a directory for the bot
   - Create a docker-compose.yml file with the example above
   - Run `docker-compose up -d`
4. Check the docker logs for the invite link:
   ```bash
   docker logs ban-appeal-bot
   ```
5. Use the invite link from the logs to add the bot to your server
6. Use `/setup` to configure the bot

## Configuration

The bot stores its configuration in the `config` directory, which is persisted through the Docker volume mount. Each server (guild) has its own configuration directory containing:
- format.json: Bot settings, message format, whitelisted roles
- error.json: Error messages, Steam ID validation messages
- logs.json: Log channel configuration

## Support

For issues or suggestions, please open an issue on GitHub.

## Built With AI

This bot was developed with the assistance of Claude AI technology. From implementing modern Discord features to solving specific challenges in the code, AI played a significant role in the development of this bot.

## License

This project is open source and available under the MIT License.
