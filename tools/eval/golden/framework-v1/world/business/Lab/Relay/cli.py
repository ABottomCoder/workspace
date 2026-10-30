"""Relay CLI: drain the inbox, send a reply.

  python cli.py drain --profile <p>
  python cli.py send <file> <channel_id> --profile <p>
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://discord.com/api/v10"


def drain(profile):
    path = os.path.join(HERE, "inbox", f"{profile}.jsonl")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    open(path, "w", encoding="utf-8").close()
    for line in lines:
        print(line)


def send(file, channel_id):
    text = open(file, encoding="utf-8").read()
    token = os.environ["RELAY_BOT_TOKEN"]
    for i in range(0, len(text), 1900):  # Discord limit is 2000 chars per message
        body = json.dumps({"content": text[i:i + 1900]}).encode()
        req = urllib.request.Request(f"{API}/channels/{channel_id}/messages", data=body, method="POST",
                                     headers={"Authorization": f"Bot {token}",
                                              "Content-Type": "application/json"})
        urllib.request.urlopen(req).read()
    print(f"sent {len(text)} chars to channel {channel_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["drain", "send"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--profile", required=True)
    a = ap.parse_args()
    if a.cmd == "drain":
        drain(a.profile)
    else:
        if len(a.args) != 2:
            sys.exit("usage: send <file> <channel_id>")
        send(*a.args)


if __name__ == "__main__":
    main()
