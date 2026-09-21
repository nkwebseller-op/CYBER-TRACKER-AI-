FROM node:20-alpine AS builder

WORKDIR /app/apps/web

COPY apps/web/package*.json ./
RUN npm ci

COPY apps/web ./

# NEXT_PUBLIC_* have to be provided at build time to be baked into the
# static bundle. Falls back to safe placeholders so a build without them
# still succeeds (the app will show an "unreachable API" state).
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_WS_BASE_URL=$NEXT_PUBLIC_WS_BASE_URL

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app/apps/web

ENV NODE_ENV=production

COPY --from=builder /app/apps/web/package*.json ./
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder /app/apps/web/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
