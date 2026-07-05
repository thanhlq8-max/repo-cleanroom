# Command Evidence Privacy Model (v0.5.0)

STATUS: PRIVACY CONTRACT — this document governs the v0.5.1 evidence importer and any
future feature that touches command evidence. Changing this contract requires a dedicated
PR and maintainer approval.

## 1. What command evidence is

Command evidence is a plain-text file the USER assembles and supplies explicitly — for
example, a hand-copied excerpt of commands they remember running (`npm install`,
`py -m venv .venv`, `cargo build`). Mapping such evidence to detected artifacts helps the
user understand where artifacts came from.

Shell history is among the most sensitive files on a developer machine: it can contain
passwords typed inline, tokens in URLs, internal hostnames, and private paths. The rules
below exist because of that.

## 2. Hard rules (all versions)

1. **No default access.** The tool NEVER locates, opens, or reads any shell history file
   (PowerShell `ConsoleHost_history.txt`, `.bash_history`, `.zsh_history`, etc.) on its
   own. There is no code path that derives a history file location.
2. **Explicit input only.** Evidence enters the tool through one required argument
   (`--evidence-file <path>`). No argument, no evidence feature. There is no hidden
   default path and no directory scanning for history-like files.
3. **No execution.** Evidence lines are data. They are never executed, shell-expanded,
   or passed to any subprocess.
4. **Sanitize before persist.** Every evidence line is sanitized (section 3) before it is
   written to any output file. Raw evidence is never copied into outputs.
5. **Local only.** Evidence and its derived outputs stay in the user-selected `--out-dir`.
   The tool performs no network I/O.
6. **User owns retention.** The tool never keeps copies outside `--out-dir` and never
   caches evidence between runs.

## 3. Sanitization rules (applied per line, in order)

1. Credential-bearing URL userinfo (`scheme://user:pass@host`) → `scheme://[REDACTED]@host`.
2. Values of sensitive flags/assignments — any `key=value` or `--key value` where the key
   matches `password|passwd|pwd|token|secret|key|auth|credential|bearer` (case-insensitive)
   → value replaced with `[REDACTED]`.
3. Long opaque strings — any run of 20+ characters from `[A-Za-z0-9_\-]` that contains at
   least one digit (token/hash shape) → `[REDACTED]`.
4. Lines that still contain a protected filename pattern (per the secret guard) are kept
   only as their command word plus `[REDACTED-ARGS]`.

Sanitization is destructive by design: over-redaction is acceptable, under-redaction is a
bug (pattern B-008).

## 4. What outputs may contain

- `command_evidence.json`: sanitized lines, their classification (ecosystem/tool), and the
  artifact types they support. Never raw lines.
- `evidence_map.md`: human-readable mapping from detected artifacts to sanitized supporting
  evidence. Never raw lines.
- Neither output contains the evidence file's path content beyond the path string the user
  passed on the command line.

## 5. What the importer must not infer

- It must not guess at commands the user did not supply.
- It must not treat evidence as an instruction to scan, plan, or clean anything.
- Evidence never changes risk classification: a `SAFE`/`REVIEW`/`DANGEROUS`/`BLOCKED`
  verdict comes only from the risk policy engine, never from evidence.

## 6. Threat notes

- A malicious repository cannot inject evidence: evidence comes only from the user's
  explicit file, never from scanned repo content.
- A user who pastes real secrets into their evidence file is protected by section 3 for
  the tool's outputs; the input file itself remains the user's responsibility (the tool
  never modifies or deletes it).
