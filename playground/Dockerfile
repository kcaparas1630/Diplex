# Builds the playground's image: the Next.js standalone server on Node 22. Only for local runs; never published.
FROM node:22-slim AS build
WORKDIR /playground
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-slim
WORKDIR /playground
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build /playground/.next/standalone ./
COPY --from=build /playground/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
