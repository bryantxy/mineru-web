FROM node:20-alpine AS builder
WORKDIR /app

# 先安装依赖后再复制源码可利用缓存
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# 复制项目源码并构建静态资源
COPY . .
RUN npm run build

FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
