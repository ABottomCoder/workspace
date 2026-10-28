Nightly memory pass for {{DATE}}. Work only in this memory dir; you don't send anything.

1. Read `raw/{{DATE}}.jsonl` (the whole day) and the existing `group.md`.
2. Write `days/{{DATE}}.md`, at most 1 KB, in the chat's language: the topics, who said what worth
   remembering (by name and user id), open threads, anything you (self=true) promised or were asked
   to follow up on. Facts only, from the transcript.
3. For each member who said something durable today, update `members/<user id>.md` (create it if
   missing): first line `# <current name> (<user id>)`, then short bullets. Merge, don't append
   duplicates; drop what is clearly outdated; stay under 1 KB.
4. Update `group.md` (≤ 2 KB): running topics, in-jokes, recurring events, promises still open.
5. Profile limits, same as in your conduct rules: only what people said or did in this chat; never
   health, politics, religion, sexuality, real identity, address, workplace or finances.
6. Print one line: what you wrote.
