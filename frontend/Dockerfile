FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=/
ARG VITE_API_TIMEOUT_MS=15000
ARG VITE_USE_MOCK_FIXTURES=false
ARG VITE_PUBLIC_REGISTRATION_ENABLED=false

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_API_TIMEOUT_MS=$VITE_API_TIMEOUT_MS \
    VITE_USE_MOCK_FIXTURES=$VITE_USE_MOCK_FIXTURES \
    VITE_PUBLIC_REGISTRATION_ENABLED=$VITE_PUBLIC_REGISTRATION_ENABLED

RUN npm run build

FROM nginx:1.28-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/health/live >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
