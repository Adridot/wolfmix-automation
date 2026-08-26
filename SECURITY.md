# Security policy

This project has no server, no service and no user accounts. "Security" here
means three specific things.

## What to report

**1. Data that should not be published.** If you find a project file, a vendor
document, an extracted resource, or personal data of any kind in this
repository or in its history, report it. This is the highest-priority class of
report: the repository's whole position ([`LEGAL.md`](LEGAL.md)) depends on it
being empty of such material, and it will be removed.

**2. A change that can damage a device or destroy work.** For example: a code
path that could write to a controller outside the experiment runner's own
UUIDs, that could overwrite an existing project file, that could emit a
firmware event, or that could corrupt a `.wpj` while claiming a successful
round-trip. Those invariants are listed in [`AGENTS.md`](AGENTS.md); a way
around any of them is a bug worth reporting.

**3. A claim that is wrong in a dangerous direction.** A field documented as
writable that is not, or a value range that would put a fixture somewhere it
should not go, is a safety issue and not merely a documentation error.

## How to report

Use **GitHub's private vulnerability reporting** on this repository
(*Security → Report a vulnerability*) for anything in class 1 or 2. Open a
normal issue for class 3, or for anything already public.

There is no bounty, no SLA and no team — this is one person's research project.
Expect a human answer, not a process.

## What is out of scope

- The Wolfmix controller, WTOOLS, or any vendor service. Report those to the
  manufacturer; this project is independent of them.
- Weaknesses in the vendor's own formats or links. This repository does not
  publish circumvention material and will not accept it — see
  [`LEGAL.md`](LEGAL.md).

## Supported versions

The tip of `master` is the only supported version. There are no releases yet.
