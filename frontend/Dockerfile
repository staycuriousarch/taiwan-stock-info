# 前端：Vite build → nginx 服務靜態檔
FROM node:22-alpine AS build

WORKDIR /app

# 先裝依賴，利用 layer cache
COPY package.json package-lock.json ./
RUN npm ci

# build（tsc -b && vite build）
COPY . .
RUN npm run build

# ---- 服務階段 ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
