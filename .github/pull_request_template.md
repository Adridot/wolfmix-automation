## What this changes

<!-- One or two sentences. If it touches a format claim, say which record and field. -->

## Evidence

<!-- Required for any change to a field interpretation: the single-variable manipulation,
     the diff or capture, the versions, and the status reached. Hashes, never files.
     Delete this section only for changes that touch no claim (docs wording, tooling). -->

## Checklist

- [ ] `make check` passes from the repository root, on a real corpus (not an abstention)
- [ ] No `.wpj`, `.wm`, `.wmx`, vendor document or extracted resource is included
- [ ] Unknown bytes still round-trip verbatim; no partial decode was introduced
- [ ] No invented name for an unconfirmed value; absent fields stay absent
- [ ] Standard library only — no new dependency
- [ ] If the change implies a count, an offset or a derivation, it is encoded in `tools/wpj_identities.py`
