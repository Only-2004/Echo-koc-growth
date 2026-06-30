# Beacon 前端容器（dev 模式 · 用于 docker-compose 本地）
# 生产部署走 npm run build → 腾讯云 COS 静态托管
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm ci

COPY . /app

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
