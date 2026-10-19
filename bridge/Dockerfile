# Official Node 20 image. The same tag publishes linux/amd64 and linux/arm64,
# so a 64-bit Raspberry Pi can build it. This image defaults to a dry run.
FROM node:20-bookworm-slim AS build

WORKDIR /app
COPY package.json package-lock.json tsconfig.json tsconfig.build.json ./
COPY src ./src
RUN npm ci && npm run build

FROM node:20-bookworm-slim

WORKDIR /app
ENV NODE_ENV=production
ENV STREAMR_DRY_RUN=1

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist

USER node
CMD ["node", "dist/cli.js"]
