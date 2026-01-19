# MinerU Web Docker 构建和部署指南

## 版本信息

- **当前版本**: v2.8.0
- **更新内容**:
  - 修复 PDF 文件预览/下载跨域问题
  - 新增识别区域高亮显示功能
  - 使用 PDF.js 替代 iframe 进行 PDF 渲染

## 快速开始

### 方式一：使用预构建镜像（推荐）

如果您希望使用预构建的镜像，可以直接运行：

```bash
# NVIDIA GPU 环境
docker-compose up -d

# 华为昇腾 NPU 环境
docker-compose -f docker-compose.npu.yml up -d
```

### 方式二：本地构建镜像

#### 1. 使用构建脚本

```bash
# 给脚本添加执行权限
chmod +x build-docker.sh

# 运行构建脚本
./build-docker.sh

# 或者指定版本和镜像仓库
VERSION=v2.8.0 REGISTRY=your-registry/ ./build-docker.sh
```

#### 2. 使用 docker-compose 构建

```bash
# NVIDIA GPU 环境 - 构建并启动
docker-compose up -d --build

# 华为昇腾 NPU 环境 - 构建并启动
docker-compose -f docker-compose.npu.yml up -d --build
```

#### 3. 手动构建镜像

```bash
# 构建前端镜像
cd frontend
docker build -t mineru-web-frontend:v2.8.0 .
cd ..

# 构建后端镜像 (NVIDIA GPU)
cd backend
docker build -t mineru-web-backend:v2.8.0 .
cd ..

# 构建后端镜像 (华为昇腾 NPU)
cd backend
docker build -f npu.Dockerfile -t mineru-web-backend-npu:v2.8.0 .
cd ..
```

## 环境变量配置

在运行前，请确保配置以下环境变量（可在 `.env` 文件中设置）：

```bash
# 版本号（可选，默认 v2.8.0）
VERSION=v2.8.0

# 镜像仓库前缀（可选，用于推送到私有仓库）
REGISTRY=your-registry/

# MinIO 端点（可选，默认 minio:9000）
MINIO_ENDPOINT=minio:9000

# Worker 副本数量（可选，默认 1）
WORKER_REPLICAS=1
```

## 镜像说明

| 镜像名称 | 说明 | 架构 |
|---------|------|------|
| `mineru-web-frontend:v2.8.0` | 前端 Web 界面 | amd64/arm64 |
| `mineru-web-backend:v2.8.0` | 后端服务 (NVIDIA GPU) | amd64 |
| `mineru-web-backend-npu:v2.8.0` | 后端服务 (华为昇腾 NPU) | arm64 |

## 推送到镜像仓库

```bash
# 登录到镜像仓库
docker login your-registry

# 推送前端镜像
docker tag mineru-web-frontend:v2.8.0 your-registry/mineru-web-frontend:v2.8.0
docker push your-registry/mineru-web-frontend:v2.8.0

# 推送后端镜像
docker tag mineru-web-backend:v2.8.0 your-registry/mineru-web-backend:v2.8.0
docker push your-registry/mineru-web-backend:v2.8.0
```

## 新功能使用说明

### PDF 预览

更新后的版本使用后端代理方式提供 PDF 文件访问，解决了之前直接使用 MinIO presigned URL 导致的跨域问题。

### 识别区域高亮

在文件预览页面，PDF 文件会显示一个"高亮区域"开关，开启后可以看到 MinerU 识别出的各种区域：

- 🟢 **文本** (text) - 绿色边框
- 🔵 **文本行** (text_line) - 蓝色边框
- 🟠 **标题** (title) - 橙色边框
- 🔴 **图片** (image) - 粉红色边框
- 🟣 **表格** (table) - 紫色边框
- 🔷 **公式** (equation) - 青色边框

## 故障排除

### 1. 前端构建内存不足

如果遇到 Node.js 内存不足错误，Dockerfile 已经添加了内存限制配置：
```dockerfile
ENV NODE_OPTIONS="--max-old-space-size=4096"
```

### 2. PDF 无法预览

确保后端服务正常运行，新版本通过 `/api/files/{id}/content` 端点代理 PDF 内容。

### 3. 高亮区域不显示

- 确保文件已经完成解析（状态为"已完成"）
- 检查 MinIO 中是否存在对应的 `_middle.json` 文件
- 打开浏览器开发者工具查看 `/api/files/{id}/regions` 接口返回

## 更新日志

### v2.8.0 (2026-01-19)

**Bug 修复**:
- 修复 PDF 文件预览/下载时的跨域问题
- 添加后端文件代理端点

**新功能**:
- 添加识别区域高亮显示功能
- 使用 PDF.js 进行 PDF 渲染
- 支持缩放控制和页码显示
- 添加高亮开关控制

**技术改进**:
- 从 middle.json 提取区域信息
- 使用 SVG overlay 实现高亮效果
