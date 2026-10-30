# ADR 006: Hosted and Self-Hosted, One Engine Image

> Status: **Accepted** · 2026-10-30

## Context

- **Some consumers want to call a service; others must keep documents on their own network.**
- **A hosted engine costs CPU per page,** so anyone with its URL could use it freely or flood it.
- **A self-hosted engine on a private network needs little or no authentication.**

## Decision

- **One engine image serves both modes.** It knows nothing about customers.
- **The hosted service adds a gateway in front of the engines:** API keys and rate, concurrency and size limits. It may be built or managed ([ADR 001](001-architecture.md) §9).
- **Self-hosted engines have authentication off by default,** or a single static key set by environment variable.
- **Both modes are free** ([ADR 007](007-mit-licence.md)). The gateway's limits exist for abuse control, not billing.

## Consequences

- **The engine stays stateless in both modes;** all customer state lives in the gateway.
- **Releases need discipline:** versioned images, an API version in every request, and an SDK that reports an engine that is too old.
- **Self-hosted operators own their LibreOffice patching,** so security releases must be published promptly.
