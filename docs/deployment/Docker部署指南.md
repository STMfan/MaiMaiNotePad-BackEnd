# Docker 部署指南

## 概述

本文档介绍如何使用 Docker Compose 部署 MaiMNP Backend 应用的 Redis 缓存服务。

## 前置要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 5GB 可用磁盘空间

## 快速开始

### 1. 配置环境变量

复制环境变量模板文件：

```bash
cp docker/.env.docker docker/.env
```

编辑 `docker/.env` 文件，根据实际情况修改配置：

```bash
# Redis 配置
CACHE_PORT=6379
CACHE_PASSWORD=your-secure-password  # 生产环境强烈建议设置密码
```

### 2. 启动 Redis 服务

```bash
# 进入 docker 目录
cd docker

# 启动服务（后台运行）
docker-compose up -d redis

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f redis
```

### 3. 验证 Redis 连接

```bash
# 使用 redis-cli 连接（无密码）
docker exec -it maimnp-redis redis-cli ping

# 使用 redis-cli 连接（有密码）
docker exec -it maimnp-redis redis-cli -a your-password ping

# 预期输出：PONG
```

### 4. 配置应用连接 Redis

确保应用的 `.env` 文件中包含正确的 Redis 配置：

```bash
CACHE_ENABLED=true
CACHE_HOST=localhost  # 如果应用在容器外运行
# CACHE_HOST=redis    # 如果应用在容器内运行
CACHE_PORT=6379
CACHE_PASSWORD=your-secure-password  # 与 Docker 配置保持一致
```

## 服务管理

**注意**：所有 docker-compose 命令需要在 `docker/` 目录下执行，或使用 `-f` 参数指定配置文件路径。

### 启动服务

```bash
# 方式 1：在 docker 目录下执行
cd docker
docker-compose up -d

# 方式 2：在项目根目录使用 -f 参数
docker-compose -f docker/docker-compose.yml up -d

# 仅启动 Redis
docker-compose up -d redis
```

### 停止服务

```bash
# 停止所有服务
docker-compose stop

# 仅停止 Redis
docker-compose stop redis
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 仅重启 Redis
docker-compose restart redis
```

### 删除服务

```bash
# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除容器和数据卷（警告：会删除所有缓存数据）
docker-compose down -v
```

## 数据持久化

### 数据卷位置

Redis 数据存储在 Docker 数据卷中：

```bash
# 查看数据卷
docker volume ls | grep maimnp-redis-data

# 查看数据卷详细信息
docker volume inspect maimnp-redis-data
```

### 备份数据

```bash
# 备份 RDB 文件
docker exec maimnp-redis redis-cli BGSAVE
docker cp maimnp-redis:/data/dump.rdb ./backup/dump-$(date +%Y%m%d-%H%M%S).rdb

# 备份 AOF 文件
docker cp maimnp-redis:/data/appendonly.aof ./backup/appendonly-$(date +%Y%m%d-%H%M%S).aof
```

### 恢复数据

```bash
# 停止 Redis 服务
docker-compose stop redis

# 复制备份文件到数据卷
docker cp ./backup/dump.rdb maimnp-redis:/data/dump.rdb
docker cp ./backup/appendonly.aof maimnp-redis:/data/appendonly.aof

# 启动 Redis 服务
docker-compose start redis
```

## 监控和调试

### 查看日志

```bash
# 实时查看日志（在 docker 目录下）
cd docker
docker-compose logs -f redis

# 或在项目根目录使用 -f 参数
docker-compose -f docker/docker-compose.yml logs -f redis

# 查看最近 100 行日志
docker-compose logs --tail=100 redis
```

### 进入容器

```bash
# 进入 Redis 容器
docker exec -it maimnp-redis sh

# 使用 redis-cli
docker exec -it maimnp-redis redis-cli
```

### 健康检查

```bash
# 查看健康状态
docker inspect maimnp-redis | grep -A 10 Health

# 手动执行健康检查
docker exec maimnp-redis redis-cli ping
```

### 性能监控

```bash
# 查看 Redis 信息
docker exec maimnp-redis redis-cli INFO

# 查看内存使用
docker exec maimnp-redis redis-cli INFO memory

# 查看统计信息
docker exec maimnp-redis redis-cli INFO stats

# 实时监控命令
docker exec -it maimnp-redis redis-cli MONITOR
```

## 配置说明

### Redis 配置文件

Redis 配置文件位于 `configs/redis.conf`，主要配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `maxmemory` | 2gb | 最大内存限制 |
| `maxmemory-policy` | allkeys-lru | 内存淘汰策略 |
| `appendonly` | yes | 启用 AOF 持久化 |
| `appendfsync` | everysec | AOF 同步策略 |
| `save` | 多个规则 | RDB 持久化触发条件 |

### Docker Compose 配置

`docker-compose.yml` 主要配置项：

| 配置项 | 说明 |
|--------|------|
| `ports` | 端口映射，默认 6379:6379 |
| `volumes` | 数据持久化和配置文件挂载 |
| `command` | Redis 启动参数 |
| `healthcheck` | 健康检查配置 |
| `deploy.resources` | 资源限制（CPU 和内存） |

## 生产环境部署

### 安全配置

1. **设置强密码**

```bash
# 在 docker/.env 文件中设置
CACHE_PASSWORD=your-very-strong-password-here
```

2. **限制网络访问**

修改 `docker/docker-compose.yml`，仅暴露给应用服务：

```yaml
services:
  redis:
    # 注释掉 ports 配置，不暴露到宿主机
    # ports:
    #   - "6379:6379"
```

3. **启用 TLS（可选）**

参考 Redis 官方文档配置 TLS 加密传输。

### 性能优化

1. **调整内存限制**

根据实际需求修改 `maxmemory` 配置：

```yaml
command: >
  redis-server
  --maxmemory 4gb  # 增加到 4GB
```

2. **调整持久化策略**

高性能场景可以禁用 AOF：

```yaml
command: >
  redis-server
  --appendonly no
```

3. **调整资源限制**

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # 增加 CPU 限制
      memory: 4G       # 增加内存限制
```

### 高可用部署

生产环境建议使用 Redis Sentinel 或 Redis Cluster：

- **Redis Sentinel**：主从复制 + 自动故障转移
- **Redis Cluster**：分布式部署 + 数据分片

详细配置请参考 Redis 官方文档。

## 故障排查

### 常见问题

#### 1. 连接被拒绝

**症状**：应用无法连接到 Redis

**解决方案**：

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 检查端口是否正确
docker port maimnp-redis

# 检查防火墙规则
# macOS
sudo pfctl -s rules | grep 6379
```

#### 2. 内存不足

**症状**：Redis 日志显示内存不足错误

**解决方案**：

```bash
# 查看内存使用
docker exec maimnp-redis redis-cli INFO memory

# 手动清理过期键
docker exec maimnp-redis redis-cli --scan --pattern "*" | xargs docker exec maimnp-redis redis-cli DEL

# 增加 maxmemory 限制（修改 docker-compose.yml）
```

#### 3. 数据丢失

**症状**：重启后缓存数据丢失

**解决方案**：

```bash
# 检查数据卷是否存在
docker volume ls | grep maimnp-redis-data

# 检查持久化配置
docker exec maimnp-redis redis-cli CONFIG GET save
docker exec maimnp-redis redis-cli CONFIG GET appendonly

# 手动触发保存
docker exec maimnp-redis redis-cli BGSAVE
```

#### 4. 性能下降

**症状**：Redis 响应变慢

**解决方案**：

```bash
# 查看慢查询日志
docker exec maimnp-redis redis-cli SLOWLOG GET 10

# 查看客户端连接数
docker exec maimnp-redis redis-cli CLIENT LIST

# 检查内存碎片率
docker exec maimnp-redis redis-cli INFO memory | grep fragmentation
```

## 降级模式

如果 Redis 服务不可用，应用会自动降级到数据库访问模式。

### 临时禁用缓存

修改应用的 `.env` 文件：

```bash
CACHE_ENABLED=false
```

重启应用后，所有缓存操作将被跳过，直接访问数据库。

### 验证降级模式

```bash
# 停止 Redis 服务
docker-compose stop redis

# 应用应该继续正常运行，但性能会下降
# 查看应用日志，应该看到降级相关的警告信息
```

## 参考资源

- [Redis 官方文档](https://redis.io/documentation)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Redis 配置参考](https://redis.io/docs/management/config/)
- [Redis 持久化指南](https://redis.io/docs/management/persistence/)
