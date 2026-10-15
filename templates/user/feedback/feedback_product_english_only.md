---
name: feedback_product_english_only
description: Product-facing output in the org's working language; private chat language is a convenience, not a comprehension aid
metadata:
  type: feedback
---
All product-facing text (tickets, reports, PRs, messages to others, CLI output, UI strings, code/comments, log lines) must be in the org's working language (default English). A different language may be used in private chat with the user purely as a convenience.

**Don't infer the wrong reason for the chat language.** If the user prefers another language for long replies, it is usually reading speed, not comprehension. Never offer a translated companion of an artifact as a comprehension aid, and don't treat their choice of language in one message as a request to reply in it. Short and medium replies in the working language need no translation.

**How to apply:** set the working language in the business `CLAUDE.md` (product output) and the conversation language in `user/profile.md`; never let the private-chat language leak into product output. Switch to the user's preferred language only for long, dense replies where reading speed pays. If the real reason to withhold a document from someone is its content, say so; don't hide behind language.
