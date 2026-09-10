FROM node:26-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm@9.15.0

# Gesamtes Repo kopieren (.dockerignore schließt node_modules/dist aus)
COPY . .

RUN pnpm install --frozen-lockfile || pnpm install
# Baut Frontend + Workspace-Abhängigkeit (@documind/shared)
RUN pnpm --filter @documind/frontend... build

FROM nginx:alpine

COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
