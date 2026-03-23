FROM node:18-alpine

WORKDIR /app

# Önce sadece dependency dosyalarını kopyala (cache optimizasyonu)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Uygulama kodunu kopyala
COPY src/ ./src/

# Non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8000

CMD ["node", "src/index.js"]
