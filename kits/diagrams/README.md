# diagrams — architecture and data-flow diagram standard

A standard for architecture and data-flow diagrams in any project (design docs, study material, READMEs,
HTML pages), plus the tools that enforce it. It came out of many rounds of iteration on a large set of
system-design diagrams that were checked by independent reviewers.

| File | What |
|---|---|
| `shapes.py` | shape library: every component is generated, never hand-drawn |
| `check_arrows.py` | machine check: no solid arrow may start at a storage shape |
| `render.py` | render an SVG to PNG with headless Chrome so it can be looked at |
| `legend.svg` | the legend to place under diagrams (shapes + arrow semantics) |

Usage from Python: `sys.path.insert(0, "<workspace>/kits/diagrams"); from shapes import *`.
CLI: `python shapes.py <kind> x y w h "title" ["sub"]` prints one snippet.

## 1. Component shapes (C4 model + cloud conventions)

There is no single industry standard; the C4 model is the most widely used vendor-neutral convention
(database cylinder, queue pipe, grey external box); the object-store bucket and CDN cloud follow cloud-vendor icons.

| Component | Shape | `shapes.py` | Colour (fill / stroke) |
|---|---|---|---|
| Service / compute | rounded rectangle | `service` | `#eef2ff` / `#2563eb` |
| Gateway / load balancer | hexagon | `lb` | as service |
| Client / user | rounded box | `client` | `#fff7ed` / `#c2410c` |
| External system (third party, the other side's service) | grey dashed box | `external` | `#f1f5f9` / `#64748b` |
| Database (incl. coordination stores such as ZooKeeper / etcd) | vertical cylinder | `db` | `#ecfdf5` / `#047857` |
| Cache (in memory, may be lost) | amber dashed cylinder | `cache` | `#fefce8` / `#a16207` |
| Message queue / log / pub-sub | horizontal pipe | `mq` | `#f5f3ff` / `#7c3aed` |
| Object store | bucket | `obj` | `#f0f9ff` / `#0369a1` |
| CDN / edge | cloud | `cdn` | `#f0f9ff` / `#0284c7` |

- **Always generate shapes with `shapes.py`.** It keeps the style consistent across projects, and every shape
  carries `data-kind` / `data-bbox` for the machine check.
- Choose the shape by **process role**, not by "has a disk": a node you design that actively calls others
  (broker, data node, replica) is a `service`; a store that is read and written gets a storage shape.

## 2. Arrow semantics (all diagrams)

1. **Solid = synchronous call**, caller → callee. **Responses are not drawn**; put the return value in the
   request label ("get signed URL", "query → top 5").
2. **Dashed = asynchronous event**, along the event flow: producer → queue → consumer (also when the consumer pulls).
3. **Storage never starts a solid arrow**; storage is only pointed at ("read X", "write X"). Exceptions are dashed
   only: CDC/binlog, object-store completion events, async replication, queue outflow.
4. CDN miss = CDN → origin (solid, "miss: fetch from origin").
5. Long-lived push (WebSocket / long-poll return) and third-party webhooks: solid from the initiator to the receiver.
6. Colour shows **which path** (overview diagrams colour each path); solid/dashed shows **sync/async**. The two are independent.
7. Lines that are not calls (hash-ring arcs, state-machine transitions, bit-field bars) are exempt from 1-5 but
   must never suggest that storage initiates a call.
8. One legend line under every diagram: `solid = synchronous call (caller → callee, response not drawn) ·
   dashed = asynchronous event (along the event flow)`.

## 3. Content

- **Data flow, not a component list.** Stores name their content or key (`messages (channel_id, seq)`); services
  name their job; the design's correctness crux (idempotency key, ID issuer, outbox, fencing…) is drawn on the box
  that enforces it.
- **Storage shapes carry the product name** (`MySQL`, `Cassandra`, `Redis`, `Kafka`, `S3`…), consistent with the
  text, plus a **storage-choice table** under the diagram: component | choice | why (access pattern → matching
  property; no "high performance" filler) | not chosen (one-line reason). If the source names no product, say
  "unspecified; typical choice".
- **Control plane and data plane are two hops** (get address/credentials, then move bytes), never one arrow.
- Number the paths: main write W1…, main read R1… (or colour per path + ①②③).

## 4. Explanatory material: the three-diagram method (when needed)

Documents meant to help someone understand (study notes, onboarding, design-review walkthroughs) get three
diagrams per system:

1. **Trunk:** the first whiteboard stroke, 5-8 boxes, plus a footer "when digging deeper, add in order: ① → ② → ③".
2. **Architecture (paths coloured):** **one diagram with every path**, laid out on a grid, short straight lines,
   one colour and number per path, main path bold. Do not split it into swim lanes (too fine), and do not let it
   become as tangled as the final-state diagram.
3. **Final state:** every mechanism together, for self-checking.

Pure engineering design docs need only diagram 2 plus the storage-choice table.

## 5. Readability and technical constraints (hard)

- Text stays inside its box, never on a line or overlapping; labels sit next to their arrow; arrows do not cross
  unrelated boxes; aim for zero crossings.
- Plain SVG only: `rect text tspan line path polyline polygon circle ellipse g`; no foreignObject, CSS classes or
  external resources (renders inline in HTML and in hosted pages). **No mermaid.**
- Suggested `viewBox="0 0 860 H"` (fits a ~920px page); marker ids unique per document (`arrow-<diagram id>…`).
- **Render and look at it:** `python render.py <file.svg> [scale]` (headless Chrome; set `CHROME` if it is not in a
  standard location), then open the PNG. At least two rounds.

## 6. Machine checks

- `python check_arrows.py <files…>` lists solid arrows that start at a storage shape (`data-kind` db/cache/mq/obj,
  or legacy `fill=#ecfdf5` rectangles); the total must be 0.
- **First run it on a planted violation and see a non-zero count; only then trust its 0** (an early version read
  `stroke-width` as a box width and always reported 0, and several agents used that 0 as proof;
  `lessons/verification.md`).
- For batch output from several agents, scan deliverables for markers of the old version before delivery, so a
  stale generator call has not overwritten new diagrams.
