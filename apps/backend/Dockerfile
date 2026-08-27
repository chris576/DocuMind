FROM node:26-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm@9.15.0

# Gesamtes Repo kopieren (.dockerignore schließt node_modules/dist aus)
COPY . .

RUN pnpm install --frozen-lockfile || pnpm install
# Baut Backend + Workspace-Abhängigkeiten (@paperless/shared, @paperless/config)
RUN pnpm --filter @paperless/backend... build

FROM node:26-alpine

WORKDIR /app

RUN npm install -g pnpm@9.15.0

COPY --from=builder /app/package.json ./
COPY --from=builder /app/pnpm-workspace.yaml ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/apps/backend/dist ./dist

EXPOSE 3001

CMD ["node", "dist/main.js"]
