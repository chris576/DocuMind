FROM node:26-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml* ./
COPY tsconfig.json ./
COPY vite.config.ts ./
COPY index.html ./

COPY src ./src

RUN pnpm install --frozen-lockfile || pnpm install
RUN pnpm build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
