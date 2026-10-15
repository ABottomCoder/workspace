# Profile

> The person this workspace serves. Gitignored (`user/`); follows the person across businesses.
> Business-specific identities (work email, chat IDs) belong in `business/<co>/people.md`.

## Identity

- Name: <name>
- Preferred form of address: <name / handle>
- Reporter line for report metadata: <name · email>
- Timezone: <e.g. UTC+8>

## Languages

- **Conversation:** mirror the user — reply in whatever language the user writes in.
- **Product output** (code, commits, PRs, tickets, docs, messages to others): the business's working
  language (business `CLAUDE.md`), default English. Never let the chat language leak into product output.
- Languages the user does NOT read (never use them, even for flavour): <none / list>

## Communication preferences

- Short by default: lead with the conclusion, stop after one or two sentences; details, reasoning,
  alternatives and risk lists only when asked. Exception: irreversible decisions and incidents, where
  the necessary risks are always stated (and only those).
- <formatting preferences: tables vs prose, emoji, headings>
- <how to report progress on long work>

## Working preferences

- <e.g. decide autonomously on reversible work; ask before anything outward-facing>
- <tools / editors / terminals the user uses>

## Persona

- If `user/persona.md` exists, apply it in conversation. It never changes code, docs, commits or
  any product output, and apps have no persona.
