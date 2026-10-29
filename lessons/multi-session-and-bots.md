# Multi-session and bots

Running chat-bot sessions and parallel agent sessions: listeners, identities, mentions, peers, and shared files and processes.

### A listener is alive only if real events arrive; backfill after any gap
**Mistake:** Listeners reconnected, logged "ready" and kept writing heartbeats while delivering no events for over an hour; one resume re-armed only the log reader while the writer was dead; another ran the supervisor as the reader; a recovery read piped through `tail` advanced the cursor past a real message and "nothing missed" was reported; a background "wait for next message" loop used a relative log path, ran from another working directory, failed its `grep` every 5 s for hours and never fired while five messages arrived.
**Root cause:** Health was measured by process-up and log freshness (heartbeats count as writes); reader and writer chains were confused; streaming sockets do not replay missed events; a cursor-advancing read consumes what truncated output hides; a wait loop treated a read error as "no new event" and its output was never read after start.
**Rule:** Liveness is the time of the last real event compared with the conversation's latest timestamp from the API. A background watcher uses absolute paths, exits non-zero on any read error instead of looping, and its output is read once a few seconds after start. After any resume, check that a live writer chain (supervisor, listener) is writing the log and a separate reader is tailing it; end-to-end proof is a real inbound message, not a self-send or a "ready" line. After any reconnect, and before saying "nothing new", backfill from the history API and read its full output, never truncated; if the cursor moved but output looks empty, refetch the gap by time range. Watch the listener log for disconnect lines so a disconnect itself triggers backfill.
**Seen:** 6

### Take identities from the registry and notify with a real mention
**Mistake:** A bot ran a whole session with its own user ID swapped with a peer's, answering mentions meant for the peer; replies landed in the wrong thread and tagged a look-alike ID; answers to a bot peer were posted without a mention, so it never received them and asked three times; plain-text "@name" notified no one.
**Root cause:** IDs were recalled from memory among similar-looking ones, and a reply felt addressed even though the peer's listener wakes only on mentions or DMs.
**Rule:** Verify your own and peers' IDs against the authoritative registry at session start; respond only to mentions of your own ID. Reply in the mentioner's own thread, using the ID from the message's sender field. Every message a bot peer must act on carries a real mention token (e.g. `<@ID>`). If a peer repeats a question you think you answered, check whether your answer mentioned them. "Sent" is not "reached the right person in the right place".
**Seen:** 5

### Treat any location others might write to as shared
**Mistake:** Two agents wrote different reports to the same generic filename in an unversioned shared folder, destroying one and silently changing a link already sent; a `git checkout -- FILE` nearly erased other sessions' edits in a shared checkout; a blind `sed` across docs rewrote correct historical statements and overwrote a peer's verdict in a shared index.
**Root cause:** Ownership was judged by how I use a location, not by who else writes there; writes were treated as additive; match sets were never previewed; an "updated" (not "created") write result was skimmed past.
**Rule:** Before writing outside your own directory, look at what is there; never overwrite a file you have not read. Read the write result: "updated" when you expected "created" means stop. Put the real disambiguator (product/scope) in filenames and first lines; when renaming a shared path, leave a pointer file. Follow a shared file's existing conventions and sign entries. No unreviewed bulk replace: `grep -n` the match set and read it first. Treat files other sessions write to as append-only unless coordinated, and work in your own worktree, not a shared checkout.
**Seen:** 4

### Re-fetch from the source before concluding anything about a conversation
**Mistake:** A peer was nudged for work answered hours earlier because the answer had been truncated out of the event stream; an action was taken on a mention edited seconds later, and a peer then wrongly diagnosed someone as having misread an ID and proposed a worse rule.
**Root cause:** "I didn't see it" was treated as "it didn't happen"; a delivered event is a snapshot, and current state cannot show what a message said at delivery.
**Rule:** Before nudging, re-deciding or diagnosing, re-read the thread via the source API rather than trusting what reached your context. When an event and a later read disagree, check the message's `edited` field and timestamps first. Before offering someone a rule, check it fits how they actually work. Fix both directions of a lossy pipe.
**Seen:** 3

### On every wake: re-arm first, then read every delivered event
**Mistake:** A bot read a wake event but did not re-arm its listener and missed messages for hours, twice despite a written rule; another bot, woken by thread-reply mentions, read only top-level messages and answered nothing.
**Root cause:** Re-arming depended on habit; the wake routine ignored the events actually delivered, and the shared reader tool was blind to replies.
**Rule:** The re-arm call is the first tool call of any turn started by a listener notification. Then read the full list of received events, threads included, and reply in the named thread. When a habit-based mistake repeats, add a mechanism (e.g. a hook that blocks ending the turn while the listener is down). When the defect is in a shared tool, fix the shared tool once instead of per-bot workarounds.
**Seen:** 2

### Verify a process is yours before killing it
**Mistake:** On resume, a running supervisor was killed because one's own log was stale; it belonged to a peer bot, orphaning its listener.
**Root cause:** All supervisors have identical command lines; "one is running and my log is stale" says nothing about ownership.
**Rule:** Kill a process only after confirming its cwd is your own directory (`lsof -a -p <pid> -d cwd -Fn`). If none match, your chain is down: start fresh rather than hunting unowned processes.
**Seen:** 1

### Ask the peer before duplicating their action
**Mistake:** Unsure whether a peer had already informed a stakeholder of an incident, a full duplicate report was sent; the peer had already done it.
**Root cause:** The jump went from "the premise changed" to the expensive action, skipping a one-line probe.
**Rule:** When the uncertainty is whether a peer already did something, ask the peer first. Duplicate independently only if they are unreachable or being wrong is unrecoverable. Do not invert this into "assume the peer handled it".
**Seen:** 1

### Replayed or backlog messages must carry their age
**Mistake:** A catch-up replay delivered a 52-day-old question formatted like a new one; only a raw epoch revealed its age.
**Root cause:** Being woken almost always means something new, so the exception was not questioned.
**Rule:** Catch-up output shows each item's age, flags old items, and labels the batch by its oldest item. As reader, check the timestamp before the content. Do not discard old backlog wholesale: check whether it was ever answered, and if not, answer it and admit the miss.
**Seen:** 1

### Recurring duties live in a file and with a real person, not a session
**Mistake:** A dated "awaiting client confirmation" list named a bot session as its periodic reviewer; the sessions behind that bot name are replaceable and do not inherit unwritten duties.
**Root cause:** Names have continuity, context does not; duties without an artifact never reach handoffs, and a dated stale list looks reviewed.
**Rule:** Put review, expiry and watch duties in a file the next session reads, and assign them to a human owner (sessions only execute). Test: "if this session vanished now, who would know to do this?"
**Seen:** 1

### Send as the bot, never through a tool authenticated as the human
**Mistake:** A bot posted through an integration authenticated as the approver's personal account, so its recommendation appeared as the approver's own position and another bot relayed it as such.
**Root cause:** The tool gave no hint whose identity it sends under; the send simply succeeded.
**Rule:** In a bot session, send only with the bot's own credentials; reading via the user-authenticated tool is fine. If a misattributed send slips out, post a correction as the bot in the same thread immediately, stating it is not the approver's approval. A `channel_not_found` on a bot DM usually signals the wrong identity, not the wrong channel id.
**Seen:** 1

### Verify that each outgoing message actually landed
**Mistake:** Three replies in a row never reached the person, who waited about 50 minutes.
**Root cause:** Malformed tool-call syntax made the send fail silently.
**Rule:** After each important send, read the latest channel message and confirm it is yours; resend if not. Emit well-formed tool calls every time; the check is the safety net.
**Seen:** 1

### Granting authority includes updating the listener allowlist
**Mistake:** New authorities' DMs were silently dropped by the bot listener's sender allowlist, so they thought the bot was dead.
**Root cause:** The authority change was recorded but the listener config was not updated.
**Rule:** Whenever someone gains authority over a bot's work, add them to its listen/DM allowlist at the same time and confirm one of their messages gets through.
**Seen:** 1
