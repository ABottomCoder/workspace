# Git and release

Lessons about branching, pull requests, review, merging, and getting the right code onto a server and proving it is running.

### Treat deploy copy and build exit codes as unproven
**Mistake:** `rsync -R $(git diff --name-only) host:dest` exited 0 while copying only some files; another rsync without `--delete` left a file deleted in git on the server, which broke the image build while the build command still exited 0.
**Root cause:** Word-split file lists with `-R` are fragile, rsync never removes files, and exit codes were taken as proof.
**Rule:** Use `rsync -a --files-from=<list> ./ host:dest/` for git-diff file sets, then grep a unique marker from each changed file on the target. After syncing across real history, remove what git deleted (`git diff --name-status <deployed> HEAD --diff-filter=D`); use `--delete` only if the target holds no host-only files. Check build output for the expected number of artifacts instead of the exit code.
**Seen:** 2

### Green tests and an owner's "merge it" are not a code review
**Mistake:** Merged a large PR into the integration branch after build, typecheck and tests passed because the owner wanted it on test; nobody read the diff, and it duplicated a teammate's open PR.
**Root cause:** Treated owner approval plus green tests as the full merge gate; tests do not cover authz, money paths or message-origin checks.
**Rule:** When team review is the norm, open the PR and stop until a human reviewer approves. Never merge a PR nobody reviewed line by line; at minimum run an independent code review and resolve must-fix findings. If review is skipped under time pressure, say so explicitly. Check for overlapping open PRs again before merging.
**Seen:** 2

### "Merged", "deployed" and "working" are separate facts; prove each by content
**Mistake:** Treated "merged" as implying deployed and working (a PR declined while thought merged, a test environment behind the branch, a package needing rebuild); used `git merge-base --is-ancestor` as proof a change was included.
**Root cause:** The rest usually follows a merge, so the exceptions go unchecked; ancestry shows reachability, not that content survived a later revert, overwrite or squash.
**Rule:** When reporting done, state which facts hold: merged (PR API), deployed (environment version endpoint), working (behavior against the built artifact). Prove a change landed by content at the target (`git show <sha>:<path>`, grep the artifact), never by ancestry. Tell whoever is waiting which fact is still missing.
**Seen:** 2

### Never run destructive git without confirming state, and never to get past an error
**Mistake:** In `git checkout main && git reset --hard origin/main && ...` the checkout aborted, so the reset discarded 20 commits on the feature branch; elsewhere `git checkout origin/<branch> -- .` was used to get past a shell glob error and wiped uncommitted work.
**Root cause:** Destructive commands ran without checking the preceding step succeeded, and were used as a convenience for problems unrelated to the working tree.
**Rule:** `reset --hard`, `checkout -- .` and `clean -fd` never fix an erroring command; fix the command. Before any of them, check `git branch --show-current` and `git status`, and commit, stash or push real work. Treat "Aborting" as a hard stop. Fast-forward a shared branch with `git push origin <feature>:<target>` rather than local checkout/reset.
**Seen:** 2

### Shared branches change only through PRs; approval of content is not approval of process
**Mistake:** Read "approved to put this on staging" as permission to push directly to the shared develop branch, and a maintainer reverted it; ops UIs that auto-sync config to main can likewise bypass review.
**Root cause:** Merged "what" (should this ship) with "how" (the integration process); a PR is where disagreement surfaces before commit, not after via revert.
**Rule:** Shared branches (develop, main, release/*) always go through a PR; confirm the process separately from the approval and default to the most conservative one. Pause whenever typing `push origin HEAD:<shared branch>`. Use operational UIs read-only and make config-as-code changes on a feature branch via PR.
**Seen:** 2

### List open PRs before starting any change
**Mistake:** Built a full fix and opened a PR while a teammate's PR from the day before already fixed the same issue more completely.
**Root cause:** Treated the duplicate check as a merge-time step, not a start-of-work step.
**Rule:** When a task is accepted, before writing code, list open PRs and search titles, descriptions and branches for the area or files involved. If one exists, review or extend it instead of building a parallel fix.
**Seen:** 1

### Verify a repo's real base branch before branching
**Mistake:** Branched off `master` in a Gitflow repo; the PR targeted `develop` and dragged in hundreds of unrelated commits.
**Root cause:** Trusted a workspace-wide "base branch" note that was only true for other repos.
**Rule:** In an unfamiliar repo, check long-lived branches, recent merge targets and repo-level docs before branching. If both `master` and `develop` exist, assume Gitflow: branch from and target `develop` unless told otherwise.
**Seen:** 1

### Don't ship a drifted source file for a one-line fix
**Mistake:** Rebuilt and copied a whole compiled file for a one-constant fix; local source also held parked, undeployed features that would have shipped with it.
**Root cause:** Assumed "my change is small" and skipped the dry-run diff on a file known to have diverged from production.
**Rule:** Before deploying, diff the built artifact against what is running (checksum dry run plus diff against the production backup). When source is ahead of production, patch the running artifact surgically or build from a clean branch at the deployed revision.
**Seen:** 1

### Plan multi-PR merges so only one deploy pipeline runs
**Mistake:** Merged two stacked PRs minutes apart into an auto-deploying branch; each started its own pipeline, wasting one and risking a race on the same environment.
**Root cause:** Treated each PR as a separate event although the top one already contained the lower one.
**Rule:** Plan the batch before merging. For stacked PRs, merge only the top one; for independent PRs, merge back to back and let only the last pipeline run. Afterwards confirm exactly one pipeline is running.
**Seen:** 1

### Validate CI steps in a clean environment
**Mistake:** A monorepo pipeline ran typecheck before build; it passed locally and failed in CI with "cannot find module" for a sibling package.
**Root cause:** Workspace packages resolve each other's types from emitted `dist/*.d.ts`, and stale local build output hid the ordering gap.
**Rule:** Before trusting a local pass, clear build artifacts (`dist`, `*.tsbuildinfo`) and run pipeline steps in order. Build before typecheck when packages consume each other's built types. Reproduce a CI failure locally to confirm the fix.
**Seen:** 1

### Test, then commit, then update every deliverable individually
**Mistake:** Committed and pushed before local testing; later updated one report and skipped the others.
**Root cause:** Treated the workflow order as optional and "update reports" as a single action.
**Rule:** Order: implement, test, self-review, commit, update reports, push. After each change round, list every deliverable that must change and update each explicitly.
**Seen:** 1

### Automated output that flips a strategic flag needs its own confirmation
**Mistake:** An optimizer re-run changed a risk flag from "off" (set deliberately months earlier) back to a numeric value; the commit listed only the tuned values, and the flip rode through several releases until someone asked where it came from.
**Root cause:** Optimizer, search and batch-refactor output mixes values with design decisions; the tool does not know why a flag was set.
**Rule:** Separate values (thresholds, sizes: apply as optimized) from strategic flags (on/off switches, stop-loss modes, skipped legs, enabled slots). When automated output flips a strategic flag relative to its previous value, stop, tell the user it reverses an earlier design decision, and get confirmation before committing.
**Seen:** 1

### Commit messages state flips, production-affecting changes and why
**Mistake:** A commit message described only the routine part of a change; the load-bearing part (a strategic flag flip) was invisible in history.
**Root cause:** Kept the message short at the cost of the information a later reader needs.
**Rule:** Every commit message names any strategic-flag flip, any production-affecting behaviour change, and the user-visible problem it addresses. Long bodies are fine; omitting load-bearing facts is not. Code committed before real-runtime validation says "UNVERIFIED + how to verify" in the body.
**Seen:** 1
