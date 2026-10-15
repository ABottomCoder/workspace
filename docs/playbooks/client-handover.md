# Client Prototype to Production: Intake, Estimate, Pricing, Build, Handover

Applies when: a client has built a prototype (single page, frontend only, mock data), typically with a no-code or AI app builder, and wants it turned into a production system.

The full build process is `docs/playbooks/ai-project-playbook.md` (lite version: `docs/playbooks/ai-project-playbook-lite.md`). This document keeps only the steps specific to taking over a client prototype.

## Roles

| Role | Owns |
|---|---|
| Account manager | Client communication, pricing, contract (playbook section 0.2) |
| Project lead | Scope decisions (G2), sign-off on requirements and estimate, acceptance decision; does not read code |
| Lead AI | Writes documents; dispatches one-shot agents for development, review and acceptance per playbook section 2.4; does no heavy work itself |

## Stage 0: Intake

- Input: from the account manager, the client name, the prototype's project ID or link, and chat history with the client.
- Output: create the project directory `<project>/` with `<project>/DEVDOC.md` (template `templates/project/DEVDOC.md`) and `<project>/CLAUDE.md` (template `templates/project/CLAUDE.md`); record the source in DEVDOC.

## Stage 1: Requirements

1. Takeover-specific step: read the prototype code and the founder's chat history. Capture the pages and flows already built, the data model inferred from code, rules already implemented, what is mock data, and things mentioned in chat but missing. Write the results straight into the requirements document draft; no separate takeover document.
2. Then follow playbook stages 1 and 2: open questions live in the requirements document; client-must-answer questions and the client version go out via the account manager; the project lead confirms before freeze.

## Stage 2: Effort estimate

- Effort is a column of the requirements feature list, estimated per playbook section 5; no separate effort document (playbook section 2.5).
- Re-estimate once after the client answers; that becomes the basis for the final price.

## Stage 3: Pricing and contract (account manager)

- Price, client choice sheet and the pre-kickoff budget cap per playbook section 0.3, section 5 and appendix A3.
- Never cite another client's project delivery times externally.
- At signing, confirm in writing: MVP boundary, hosting and account ownership, who pays recurring costs, warranty period.

## Stage 4: Build (playbook stages 3 to 7)

1. Kickoff pack, foundation, parallel development, independent review and black-box acceptance follow the matching playbook stages.
2. Commits and review per playbook sections 2.1 and 2.2 (AI commits locally only; pushing is done by humans). The project lead confirms scope and acceptance, not code.
3. Security scanning (SAST, dependency and secret scans) runs as part of the local test layers before G3 (playbook section 2.8). Staging, client acceptance on a hosted environment and launch are outside the playbook and arranged by humans from the deploy-notes draft.

## Stage 5: Handover and retrospective

- Launch and transfer (code, hosting accounts, documents), done by humans per the deploy-notes draft.
- Fill in actuals per playbook section 5 (appendix A12), compare with the estimate, and calibrate appendix A13.
- Record what this project taught in the project `CLAUDE.md` and in this process.

## Open items

- [x] Heavy third-party workflow skill packs: evaluated against real project records and not adopted; no evidence they improved results. Security auditing stays with a static analyser (e.g. semgrep).
- [ ] Estimation: do not build a custom skill; prefer time-tested existing methods. Use WBS plus PERT three-point estimation as method reference, applied manually per playbook section 5.
- [ ] An estimate-vs-actual record table.
- [ ] Run the whole process end to end on a new client project and revise this document from the results.
