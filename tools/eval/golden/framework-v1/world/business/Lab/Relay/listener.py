"""Relay listener: forward Discord @mentions into a running Claude Code session.

Run it as a background task from the session. Every @mention is appended to the
profile's inbox and announced on stdout as one line; the session is woken by that
line, drains the inbox with cli.py and replies with cli.py send.
"""
import argparse
import json
import os
import sys
import tomllib
from datetime import timezone

import discord

HERE = os.path.dirname(os.path.abspath(__file__))


def load_profile(name):
    with open(os.path.join(HERE, "profiles.toml"), "rb") as f:
        return tomllib.load(f)[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    args = ap.parse_args()
    prof = load_profile(args.profile)
    inbox = os.path.join(HERE, "inbox", f"{args.profile}.jsonl")
    os.makedirs(os.path.dirname(inbox), exist_ok=True)

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"RELAY_READY {client.user}", flush=True)

    @client.event
    async def on_message(msg):
        if msg.author == client.user:
            return
        if str(msg.channel.id) not in prof["channels"]:
            return
        if client.user not in msg.mentions:
            return
        rec = {"id": str(msg.id), "channel_id": str(msg.channel.id), "author": msg.author.name,
               "content": msg.clean_content,
               "ts": msg.created_at.astimezone(timezone.utc).isoformat()}
        with open(inbox, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # one line per mention: this is what wakes the session
        print(f"MENTION {rec['id']} | {rec['author']} | {rec['content']}", flush=True)

    token = os.environ.get("RELAY_BOT_TOKEN")
    if not token:
        sys.exit("RELAY_BOT_TOKEN not set")
    client.run(token, log_handler=None)


if __name__ == "__main__":
    main()
