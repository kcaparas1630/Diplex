# ADR 004: LibreOffice Runs Through a unoserver Pool

> Status: **Accepted** · 2026-10-30 · Refined by [ADR 011](011-unoserver-pool-dispatcher.md): the engine, not unoserver's flags, recycles, times out and supervises the instances

## Context

- **The proof of concept started a fresh LibreOffice container per job.** That gives the strongest isolation, but pays LibreOffice's startup on every conversion.
- **[unoserver](https://github.com/unoconv/unoserver) (MIT) keeps LibreOffice running** and converts over a local socket.
- **Its README states its limits:** no load balancing ("you would have to implement that yourself"), a unique `--port` and `--uno-port` per instance to scale across cores, no restart of LibreOffice after a crash (it expects a service manager to restart it), and unauthenticated ports that must not be reachable from outside. Its changelog adds that memory is not reclaimed after large files, the reason for `--stop-after`.
- **One instance converts one document at a time.** The README does not say so; unoserver 3.7's code does: its XML-RPC server is the standard library's single-threaded `SimpleXMLRPCServer` ([`server.py`](https://github.com/unoconv/unoserver/blob/3.7/src/unoserver/server.py)), so a second request waits until the first is done.
- **Per-job fonts were the main reason for one process per job,** and [ADR 005](005-fonts.md) removed them.

### The 2026-10-30 Benchmark

Measured on a laptop with unoserver 3.7 and LibreOffice 25.2.3 in the root Dockerfile's image, on the 103 real DOCX samples. They are laptop numbers, to repeat on the hosting target.

- **Throughput scales with vCPUs, not instances:** 8 instances on 4 vCPUs made each conversion 2.04 times slower, and 1.19 times slower on 8 vCPUs. About 37 documents per minute per vCPU, so the pool size should be the vCPU count.
- **Memory is never reclaimed:** 233 MB idle, about 1.0 GB after 50 conversions and 1.65 GB after 303. That points to recycling after about 50 conversions and budgeting 1 to 1.5 GB per instance.
- **Latency:** median 0.15 s, p95 2.3 s, p99 about 44 s, slowest successful conversion 75 s. One document takes 189 s, so a 120 s timeout fails it.
- **A timed-out instance is not safe to reuse:** it keeps accepting requests and failing them, and `soffice.bin` outlives unoserver and keeps holding the UNO port.

## Decision

- **A pool of unoserver instances,** each with one LibreOffice, its own profile, and ports bound to localhost only.
- **Each instance is recycled** after a set number of conversions (`--stop-after`) and killed on a conversion timeout (`--conversion-timeout`).
- **A supervisor restarts instances when they exit.**
- **LibreOffice has no network access,** and each job still gets its own scratch directory, wiped afterwards.

## Consequences

- **Less CPU per conversion,** since LibreOffice no longer starts for every job.
- **Weaker isolation:** a malicious document can affect later conversions on the same instance until it is recycled. This is a deliberate trade, reviewed in the security milestone.
- **Pool size, recycle count and timeout are open decisions** ([ADR 001](001-architecture.md) §7); the benchmark above is the evidence for them.
