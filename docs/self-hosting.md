# Self-Hosting the Engine

How to run the `diplex-core` image next to your app, and what you must keep in place. The design behind it is [ADR 001](adr/001-architecture.md).

## Running It

- **One container, port 8000.** `docker run -d --name diplex-engine diplex-core` starts the API; the engine starts its pool of unoserver instances (LibreOffice) inside, and a DOCX sent in the first few seconds waits for them.
- **Give it the memory the pool needs:** about 1 to 1.5 GB per unoserver instance, from the 2026-10-30 benchmark ([ADR 004](adr/004-unoserver-pool.md)), plus a few hundred MB for the API and page rendering.
- **Stop it with `docker stop`.** The engine kills every LibreOffice process on the way out; it took under a second in CI.
- **Health checks** use `GET /health`, which needs no key and no version header.

## Settings

All settings are environment variables, checked when the engine starts; a value it can't use stops it with an error naming the variable.

| Variable | Default | What it sets |
|---|---|---|
| `DIPLEX_API_KEY` | unset (no authentication) | a key of 16 or more characters that `/render` then needs as `Authorization: Bearer <key>` ([ADR 012](adr/012-api-key-and-version.md)) |
| `DIPLEX_MAX_UPLOAD_BYTES` | 52428800 (50 MiB) | the largest request body accepted |
| `DIPLEX_MAX_PAGES` | 500 | the most pages a document may have |
| `DIPLEX_UNOSERVER_INSTANCES` | the vCPUs available to the container | how many LibreOffice instances convert DOCX files at once ([ADR 011](adr/011-unoserver-pool-dispatcher.md)) |
| `DIPLEX_CONVERTER_WAIT_SECONDS` | 30 | how long a DOCX waits for a free instance before 503 `converter_busy` |
| `DIPLEX_CONVERSION_TIMEOUT_SECONDS` | 120 | how long a conversion may run before its instance is killed and the DOCX gets 422 |
| `DIPLEX_CONVERSIONS_BEFORE_RECYCLE` | 50 | conversions an instance does before it is replaced, since LibreOffice never gives memory back |

The page and upload limits are provisional until the engine is measured on the samples.

## The Network: Inbound From Your App Only, No Outbound at All

The engine needs no outbound connections, and LibreOffice must not have any: a document can link remote images or other content, and opening it could otherwise reach your network or the internet ([ADR 013](adr/013-no-network-for-libreoffice.md)). These are yours to keep in place:

- **Keep the engine off the internet.** Its ports are for your app's server only; never publish them on a public interface. unoserver's ports are unauthenticated and already bound to the container's localhost.
- **Give the container no egress.** With Docker, put it on an internal network, and attach your app to that network as well:

  ```
  docker network create --internal diplex-engine
  docker run -d --name diplex-engine --network diplex-engine diplex-core
  docker network connect diplex-engine your-app      # your app now calls http://diplex-engine:8000
  ```

  With Docker Compose, give the engine only a network marked `internal: true`, and your app both that network and the default one. With Kubernetes, a NetworkPolicy that lists `Egress` in `policyTypes` with no egress rules, and allows ingress on port 8000 from your app's pods only; it is enforced only by a network plugin that supports NetworkPolicy.
- **Check it.** From inside the container, an outbound connection must fail:

  ```
  docker exec diplex-engine python3 -c "import socket; socket.create_connection(('1.1.1.1', 443), timeout=3)"
  ```

  This must end in `OSError: [Errno 101] Network is unreachable` (or a timeout), never return quietly. CI runs the same check on every pull request.
- **Use the key, and TLS, when traffic crosses a network you don't trust.** The key travels in clear text over plain HTTP.

## Calling It

- **`POST /render`** with `multipart/form-data` (the file in a part named `document`) and the header `Diplex-Api-Version: 1`, plus `Authorization: Bearer <key>` when the engine has a key. The contract is [openapi.json](openapi.json); [ADR 001](adr/001-architecture.md) §4 describes the response and every error code.
- **Store the results yourself,** following [ADR 001](adr/001-architecture.md) §5; the engine keeps nothing.
