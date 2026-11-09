# ADR 011: The Engine Runs, Dispatches and Recycles the unoserver Pool

> Status: **Accepted** · 2026-11-07 · Refines: [ADR 004](004-unoserver-pool.md) (how instances are recycled, timed out and supervised)

## Context

- **unoserver converts one document at a time and has no load balancing** ([ADR 004](004-unoserver-pool.md)), so something in front of the instances must hand each conversion to a free one.
- **unoserver's own limits act from inside the instance, at the wrong moment.** `--stop-after` terminates LibreOffice after the Nth request, so a request sent while it shuts down fails although its document is fine. `--conversion-timeout` terminates LibreOffice and exits, but the 2026-10-30 benchmark found `soffice.bin` outliving unoserver and holding the UNO port. Only the engine knows when a conversion starts, ends or fails.
- **LibreOffice's processes join unoserver's process group.** Measured with unoserver 3.7 and LibreOffice 24.2 started in a new session: `oosplash`, `soffice.bin` and LibreOffice's `gpg` helpers all carry unoserver's group ID. SIGKILL to the group closed both ports within 0.05 s, and the killed processes were adopted by PID 1, which must reap them. unoserver answered its `info` call 5.5 s after starting, and converts with its input in a temporary file ([unoserver 3.7 `converter.py`](https://github.com/unoconv/unoserver/blob/3.7/src/unoserver/converter.py)), so a killed conversion leaves a copy of the document behind.
- **FastAPI runs a plain `def` route in a thread pool,** and AnyIO's default limiter holds 40 threads (`CapacityLimiter(40)` in AnyIO's asyncio backend). A request waiting for an instance holds one of them.
- **The hosted gateway that this design was to size is gone** ([ADR 009](009-engine-only.md)). The concurrency question is now the consumer's: how many renders it sends at once, against the pool size.

## Decision

### Instances

- **The engine process starts the pool and owns it.** At startup it starts `DIPLEX_UNOSERVER_INSTANCES` unoserver instances, by default the vCPUs available to the container (the benchmark's one instance per vCPU), and at shutdown it kills them. The container runs one engine process, since each would start its own pool.
- **Each instance runs in its own session, so in its own process group,** with its own scratch folder holding its LibreOffice profile and temporary files, created empty at each start and deleted after. Instance `i` listens on 127.0.0.1 only: UNO port `2002 + 2i`, XML-RPC port `2003 + 2i` (the first instance keeps unoserver's default ports).
- **An instance takes conversions only once it answers unoserver's `info` call.**

### Dispatching

- **A conversion claims an idle instance and has it to itself until it ends.**
- **When none is idle, it waits** up to `DIPLEX_CONVERTER_WAIT_SECONDS` (30 s) for one, then gets 503 `converter_busy`. If no instance is running or starting, it gets 503 `converter_unavailable` at once, and also when the wait ends with instances still starting.
- **The conversion call times out** after `DIPLEX_CONVERSION_TIMEOUT_SECONDS` (120 s), above the benchmark's slowest successful conversion (75 s), and the request gets 422 `docx_conversion_failed` saying so. The one 189 s sample fails at this setting.

### Recycling and Supervision

- **The engine recycles an instance, never unoserver:** after `DIPLEX_CONVERSIONS_BEFORE_RECYCLE` conversions (50, from the benchmark's memory growth) and after any failed conversion, a timeout included, before it takes another job. A conversion in flight never sees its instance recycled. unoserver's `--stop-after` and `--conversion-timeout` are not used.
- **Recycling kills the instance's whole process group with SIGKILL,** waits until its ports close, deletes its scratch folder, and starts a fresh instance on the same ports.
- **A keeper thread per instance supervises it:** it restarts the instance when it exits on its own and retries a failed start after a delay that doubles from 1 s to 30 s.
- **The image's PID 1 stays the bash entrypoint,** which reaps the LibreOffice processes adopted after a kill (checked: bash as PID 1 left no zombies from adopted orphans).
- **All four settings are environment variables,** read and checked when the engine starts, like `DIPLEX_MAX_UPLOAD_BYTES`.

## Consequences

- **Conversions never meet a recycling instance,** and a stuck or crashed LibreOffice is gone with its whole process group, its profile and any document copy it left.
- **Isolation improves on ADR 004's trade without closing it:** a malicious document can still affect later conversions on its instance, but only successful ones, and only until that instance's next recycle. The security milestone reviews this.
- **A recycle takes an instance out for about 5.5 s,** LibreOffice's start, while the others keep serving. With one instance, DOCX requests wait for it.
- **A request can wait up to 30 s for an instance and 120 s for its conversion.** Beyond 40 concurrent requests, AnyIO queues the rest before the 30 s starts, and PDF renders and `/health` share those threads.
- **The defaults come from laptop measurements;** the load test on the samples (issue #64) confirms or changes them.
