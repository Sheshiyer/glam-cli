# Bounded project context

## Registry evidence

- Registry WorkObject: `program:operator-utilities` (`Operator Utilities`)
- Knowledge pointer: `00-meta/system-of-records.md` — placeholder, not a confirmed vault reference
- Repository: `gram-cli`

## Operating invariants

- Use Codex as the default local approval governor; other clients consume
  the same packet rather than creating competing project state.
- OmniRoute is a model-call transport beneath the project rail, not a
  project or session store.

## Fields needing review

This packet needs review for the following fields before moving to
`reviewed-held`, since this tool could not confidently source them:

- `knowledge_ref`

## Relocation boundary

This packet is draft-held. The move to a new destination outside the vault
remains blocked until this packet is reviewed, any flagged fields are
resolved, the packet change is committed, an exact manifest is approved,
and a separate live-apply approval exists.
