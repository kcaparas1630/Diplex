# ADR 013: LibreOffice Has No Network Because the Engine's Container Has None

> Status: **Accepted** · 2026-11-10

## Context

- **Convention 003 and [ADR 004](004-unoserver-pool.md) require that LibreOffice cannot reach the network.** A DOCX can link external images and other content, and LibreOffice opening an untrusted document must not fetch anything, inside the consumer's network or out.
- **The engine itself makes no outbound connections.** It receives uploads and answers them; unoserver and LibreOffice talk to it over the container's localhost.
- **Cutting off LibreOffice alone inside the container needs privileges.** A firewall rule per user (iptables owner match) needs `NET_ADMIN` and a root step in the entrypoint; a separate network namespace for LibreOffice would also cut it off from unoserver's localhost UNO port.
- **Docker and Kubernetes can deny a container all egress.** Measured with Docker 29: on a network created with `--internal`, connecting out failed with "Network is unreachable" and DNS did not resolve, while a container on the same network reached the engine.

## Decision

- **The whole engine container runs with no egress,** which covers LibreOffice without privileges or code: a Docker internal network, a Compose network marked `internal: true`, or a Kubernetes NetworkPolicy with no egress rules.
- **Operators keep this in place;** [the self-hosting guide](../self-hosting.md) says how, and gives a one-line check from inside the container.
- **The playground runs the engine this way** once it exists, and CI checks it on every pull request: from inside an engine on an internal network, an outbound connection must fail, while a sibling container reaches its `/health`.

## Consequences

- **No privileges and no extra moving parts in the image.**
- **The guarantee depends on the deployment:** an engine run on Docker's default bridge can still reach out. The image cannot enforce it alone, so the guide and the checks carry it.
- **Consumers reach the engine over a shared internal network** rather than a published port, which also keeps it off the internet.
