# Diplex Playground

A sample consumer app for the Diplex engine, never published ([ADR 016](../docs/adr/016-playground-stack.md)). It does what a real app should: its server sends each upload to the engine's `POST /render`, keeps the results in its own bucket and database ([ADR 001](../docs/adr/001-architecture.md) §5), and hands the browser short-lived presigned URLs. It never imports the engine's code.

## Run It

```
docker compose up --build        # engine, RustFS, Postgres and the playground; then open http://localhost:3000
```

The engine runs on a network with no egress, which only the playground also joins ([ADR 013](../docs/adr/013-no-network-for-libreoffice.md)). The credentials in `compose.yaml` are for local use only.

## Work on It

```
pnpm install
pnpm dev                         # http://localhost:3000; set the variables below to reach an engine, a bucket and a database
pnpm typecheck
pnpm test
pnpm build
```

| Variable | What it is |
|---|---|
| `DIPLEX_ENGINE_URL` | the engine, e.g. `http://127.0.0.1:8000` |
| `DIPLEX_API_KEY` | the engine's key, when it has one |
| `DATABASE_URL` | Postgres, e.g. `postgres://playground:playground@127.0.0.1:5432/playground` |
| `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT` | the bucket's endpoint for the server, and the one browsers reach for presigned URLs |
| `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_PREFIX` | the bucket, its credentials (server only) and the folder prefix |
