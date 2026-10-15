---
name: feedback_short_messages
description: Messages to other people (chat/ticket/PR) must be short and simple, one purpose, no evidence inline
metadata:
  type: feedback
---
When drafting a message to ANYONE other than the user (chat DMs, ticket comments, PR descriptions/comments, review requests), keep it SHORT and simple. A few sentences max. No walls of text, no multi-paragraph essays, no bullet dumps.

**Why:** long messages to colleagues are off-putting and hard to skim, and they read as AI-generated. The user's framing: no real person would want to WRITE a message that long, and nobody wants to READ one. This drifts back repeatedly across sessions (four-plus corrections), so treat it as a hard rule, not a preference.

**How to apply:**
- **Name the message's single purpose first** (question / FYI / ask for action / status), then delete every clause that serves a different purpose. An FYI is: the fact, "we're proceeding on that basis", "will keep you posted". A question contains only what the answer depends on: no status, no PR links, no "what I did".
- **Answer the question asked, don't explain the topic.** A yes/no question gets the answer + one clause of why + the action.
- **For a senior colleague, cut every sentence they could have written themselves.** The whole message is the one new fact, the one decision, your default. Target three sentences; a fourth needs a reason. If the draft has paragraphs, it is wrong.
- **Keep evidence out.** SHAs, file:line refs, numbers, quoted docs prove things to the *user*; colleagues want the conclusion and will ask for detail. Detail goes in the ticket ("details on the ticket").
- **Hard cap for a findings message:** ≤120 words, one line per finding, no inline numbers or evidence.
- No headings, numbered lists, tables or inline specs in chat. Prose only.
- Multiple unrelated points: pick the one that matters, or send separate short messages.
- **Applies to drafts shown to the user too.** A draft the user has to ask you to shorten was already too long. Draft it, halve it, then show it.
- Calibration: what a busy engineer would thumb-type on a phone. If it needs scrolling, cut.
- Internal analysis for the user can still be thorough; this is about outbound messages. Drafts still need the user's explicit go-ahead before sending ([[feedback_explicit_permission_before_sending]]).
