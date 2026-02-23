# Docker 快速开始

本文档提供 Docker Compose 的快速使用指南。详细文档请参考 [Docker 部署指南](../docs/deployment/Docker部署指南.md)。

## 快速启动

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.docker .env

# 编辑 .env 文件，设置 Redis 密码（可选）
# CACHE_PASSWORD=your-secure-password
```

### 2. 启动 Redis 服务

```bash
# 启动 Redis（后台运行）
docker-compose up -d redis

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f redis
```

### 3. 验证连接

```bash
# 测试 Redis 连接
docker exec -it maimnp-redis redis-cli ping
# 预期输出：PONG
```

### 4. 配置应用

确保应用的 `.env` 文件包含正确的 Redis 配置：

```bash
CACHE_ENABLED=true
CACHE_HOST=localhost
CACHE_PORT=6379
CACHE_PASSWORD=  # 如果设置了密码，在此填写
```

## 常用命令

```bash
# 启动服务
docker-compose up -d redis

# 停止服务
docker-compose stop redis

# 重启服务
docker-compose restart redis

# 查看日志
docker-compose logs -f redis

# 删除服务（保留数据）
docker-compose down

# 删除服务和数据
docker-compose down -v
```

## 服务配置

### Redis 配置

- **镜像**：redis:7-alpine
- **端口**：6379
- **内存限制**：2GB
- **持久化**：RDB + AOF
- **淘汰策略**：allkeys-lru

### 数据持久化

Redis 数据存储在 Docker 数据卷 `maimnp-redis-data` 中，重启容器不会丢失数据。

### 健康检查

Docker Compose 配置了自动健康检查，每 10 秒检查一次 Redis 是否响应。

## 故障排查

### Redis 无法启动

```bash
# 查看详细日志
docker-compose logs redis

# 检查端口占用
lsof -i :6379
```

### 应用无法连接 Redis

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试连接
docker exec -it maimnp-redis redis-cli ping

# 检查应用配置
cat .env | grep CACHE_
```

### 数据丢失

```bash
# 检查数据卷
docker volume ls | grep maimnp-redis-data

# 手动触发保存
docker exec maimnp-redis redis-cli BGSAVE
```

## 降级模式

如果 Redis 不可用，应用会自动降级到数据库访问模式：

```bash
# 临时禁用缓存
# 在应用的 .env 文件中设置
CACHE_ENABLED=false
```

## 更多信息

- 详细部署指南：[../docs/deployment/Docker部署指南.md](../docs/deployment/Docker部署指南.md)
- Redis 配置文件：[../configs/redis.conf](../configs/redis.conf)
- Docker Compose 配置：[docker-compose.yml](docker-compose.yml)
