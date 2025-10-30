const express = require('express');
const router = express.Router();
const os = require('os');
const fs = require('fs').promises;
const path = require('path');
const { logger } = require('../middleware/logger');

// 获取系统信息
router.get('/info', async (req, res) => {
    try {
        const info = {
            system: {
                platform: os.platform(),
                arch: os.arch(),
                hostname: os.hostname(),
                uptime: os.uptime(),
                loadAverage: os.loadavg()
            },
            memory: {
                total: os.totalmem(),
                free: os.freemem(),
                used: os.totalmem() - os.freemem()
            },
            cpu: {
                cores: os.cpus().length,
                model: os.cpus()[0]?.model || 'Unknown',
                speed: os.cpus()[0]?.speed || 0
            },
            node: {
                version: process.version,
                pid: process.pid,
                ppid: process.ppid,
                uptime: process.uptime()
            },
            environment: {
                nodeEnv: process.env.NODE_ENV || 'development',
                port: process.env.PORT || 3000
            }
        };

        res.json({
            success: true,
            data: { info }
        });
    } catch (error) {
        logger.error('获取系统信息失败:', error);
        res.status(500).json({
            success: false,
            message: '获取系统信息失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 获取磁盘信息
router.get('/disk', async (req, res) => {
    try {
        const diskInfo = {
            cwd: process.cwd(),
            __dirname: __dirname,
            free: 0,
            size: 0,
            used: 0
        };

        // 尝试获取磁盘空间信息（跨平台兼容性）
        try {
            const stats = await fs.stat('/');
            // 这里可以添加更详细的磁盘空间检查逻辑
            // 注意：获取磁盘空间信息在不同操作系统上实现不同
        } catch (error) {
            logger.warn('获取磁盘空间信息失败:', error.message);
        }

        res.json({
            success: true,
            data: { disk: diskInfo }
        });
    } catch (error) {
        logger.error('获取磁盘信息失败:', error);
        res.status(500).json({
            success: false,
            message: '获取磁盘信息失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 健康检查
router.get('/health', async (req, res) => {
    try {
        const health = {
            status: 'healthy',
            timestamp: new Date().toISOString(),
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            checks: {
                database: 'unknown', // 可以添加数据库连接检查
                filesystem: 'accessible'
            }
        };

        // 检查文件系统
        try {
            await fs.access(process.cwd());
            health.checks.filesystem = 'accessible';
        } catch (error) {
            health.checks.filesystem = 'inaccessible';
            health.status = 'unhealthy';
        }

        res.json({
            success: true,
            data: { health }
        });
    } catch (error) {
        logger.error('健康检查失败:', error);
        res.status(500).json({
            success: false,
            message: '健康检查失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 获取日志信息
router.get('/logs', async (req, res) => {
    try {
        const { level = 'info', limit = 100 } = req.query;

        // 这里可以集成实际的日志系统
        const logs = [
            {
                timestamp: new Date().toISOString(),
                level: 'info',
                message: '系统日志示例',
                context: 'system'
            }
        ];

        res.json({
            success: true,
            data: {
                logs: logs.slice(0, parseInt(limit)),
                total: logs.length
            }
        });
    } catch (error) {
        logger.error('获取日志信息失败:', error);
        res.status(500).json({
            success: false,
            message: '获取日志信息失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 获取环境变量（安全版本，只显示非敏感信息）
router.get('/env', async (req, res) => {
    try {
        const safeEnv = {
            NODE_ENV: process.env.NODE_ENV || 'development',
            PORT: process.env.PORT || 3000,
            CORS_ORIGIN: process.env.CORS_ORIGIN || '*',
            UPLOAD_MAX_SIZE: process.env.UPLOAD_MAX_SIZE || '10MB',
            JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '7d',
            MONGODB_URI: process.env.MONGODB_URI ? '已配置' : '未配置',
            JWT_SECRET: process.env.JWT_SECRET ? '已配置' : '未配置'
        };

        res.json({
            success: true,
            data: { env: safeEnv }
        });
    } catch (error) {
        logger.error('获取环境变量失败:', error);
        res.status(500).json({
            success: false,
            message: '获取环境变量失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 获取进程信息
router.get('/process', async (req, res) => {
    try {
        const processInfo = {
            pid: process.pid,
            ppid: process.ppid,
            title: process.title,
            version: process.version,
            versions: process.versions,
            arch: process.arch,
            platform: process.platform,
            argv: process.argv,
            execPath: process.execPath,
            execArgv: process.execArgv,
            env: Object.keys(process.env),
            uptime: process.uptime(),
            memoryUsage: process.memoryUsage(),
            cpuUsage: process.cpuUsage()
        };

        res.json({
            success: true,
            data: { process: processInfo }
        });
    } catch (error) {
        logger.error('获取进程信息失败:', error);
        res.status(500).json({
            success: false,
            message: '获取进程信息失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 获取网络信息
router.get('/network', async (req, res) => {
    try {
        const networkInfo = {
            interfaces: os.networkInterfaces(),
            hostname: os.hostname(),
            loadavg: os.loadavg()
        };

        res.json({
            success: true,
            data: { network: networkInfo }
        });
    } catch (error) {
        logger.error('获取网络信息失败:', error);
        res.status(500).json({
            success: false,
            message: '获取网络信息失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 系统配置信息
router.get('/config', async (req, res) => {
    try {
        const config = {
            system: {
                name: 'MaiMaiNotePad',
                version: '1.0.0',
                description: '知识管理与笔记系统',
                author: 'MaiMai Team'
            },
            features: {
                authentication: true,
                fileUpload: true,
                knowledgeManagement: true,
                adminPanel: true,
                backup: true,
                search: true
            },
            limits: {
                maxFileSize: process.env.UPLOAD_MAX_SIZE || '10MB',
                maxFilesPerUpload: 10,
                jwtExpiresIn: process.env.JWT_EXPIRES_IN || '7d'
            },
            supportedFormats: {
                documents: ['pdf', 'doc', 'docx', 'txt', 'md'],
                images: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                archives: ['zip', 'rar']
            }
        };

        res.json({
            success: true,
            data: { config }
        });
    } catch (error) {
        logger.error('获取系统配置失败:', error);
        res.status(500).json({
            success: false,
            message: '获取系统配置失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 性能监控
router.get('/performance', async (req, res) => {
    try {
        const startTime = Date.now();

        // 模拟一些基本操作来测试性能
        const memoryBefore = process.memoryUsage();

        // 执行一些基本操作
        const testArray = Array.from({ length: 10000 }, (_, i) => i);
        const testResult = testArray.reduce((sum, num) => sum + num, 0);

        const memoryAfter = process.memoryUsage();
        const endTime = Date.now();

        const performance = {
            timestamp: new Date().toISOString(),
            responseTime: endTime - startTime,
            memoryUsage: {
                before: memoryBefore,
                after: memoryAfter,
                delta: {
                    rss: memoryAfter.rss - memoryBefore.rss,
                    heapTotal: memoryAfter.heapTotal - memoryBefore.heapTotal,
                    heapUsed: memoryAfter.heapUsed - memoryBefore.heapUsed,
                    external: memoryAfter.external - memoryBefore.external
                }
            },
            cpuUsage: process.cpuUsage(),
            systemLoad: os.loadavg()
        };

        res.json({
            success: true,
            data: { performance }
        });
    } catch (error) {
        logger.error('性能监控失败:', error);
        res.status(500).json({
            success: false,
            message: '性能监控失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// 系统状态统计
router.get('/status', async (req, res) => {
    try {
        const status = {
            server: {
                status: 'running',
                uptime: process.uptime(),
                startTime: new Date(Date.now() - process.uptime() * 1000).toISOString()
            },
            memory: {
                usage: process.memoryUsage(),
                system: {
                    total: os.totalmem(),
                    free: os.freemem(),
                    used: os.totalmem() - os.freemem()
                }
            },
            cpu: {
                loadAverage: os.loadavg(),
                cores: os.cpus().length,
                usage: process.cpuUsage()
            },
            timestamp: new Date().toISOString()
        };

        res.json({
            success: true,
            data: { status }
        });
    } catch (error) {
        logger.error('获取系统状态失败:', error);
        res.status(500).json({
            success: false,
            message: '获取系统状态失败',
            error: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

module.exports = router;