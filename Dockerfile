# Use Python 3.10 as the base image for better compatibility
FROM python:3.10-slim

# Install system dependencies required for audio processing and discord.py
RUN apt-get update && apt-get install -y \
    libasound2 \
    python3-dev \
    build-essential \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY bot.py requirements.txt /app

# Install Python packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for bot token (ensure to replace this with your token securely later)
ENV DISCORD_BOT_TOKEN=""

# Run bot.py when the container launches
CMD ["python", "bot.py"]
