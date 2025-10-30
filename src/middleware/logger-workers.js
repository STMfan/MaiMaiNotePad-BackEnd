/**
 * Logger Middleware for Cloudflare Workers
 * 适配Workers运行时的日志中间件
 */

/**
 * 日志级别枚举
 */
const LOG_LEVELS = {
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
};

/**
 * 日志级别名称映射
 */
const LOG_LEVEL_NAMES = {
  0: 'ERROR',
  1: 'WARN',
  2: 'INFO',
  3: 'DEBUG'
};

/**
 * Cloudflare Workers日志记录器
 */
export class WorkersLogger {
  constructor(env, options = {}) {
    this.env = env;
    this.level = options.level || LOG_LEVELS.INFO;
    this.service = options.service || 'maimai-note-pad';
    this.environment = options.environment || 'production';
    this.enableConsole = options.enableConsole !== false;
    this.enableAnalytics = options.enableAnalytics !== false;
    this.enableKV = options.enableKV !== false;
  }

  /**
   * 格式化日志消息
   */
  formatMessage(level, message, meta = {}) {
    const timestamp = new Date().toISOString();
    const levelName = LOG_LEVEL_NAMES[level] || 'UNKNOWN';
    
    return {
      timestamp,
      level: levelName,
      service: this.service,
      environment: this.environment,
      message,
      meta: {
        ...meta,
        requestId: meta.requestId || crypto.randomUUID(),
        workerId: this.env.WORKER_ID || 'unknown'
      }
    };
  }

  /**
   * 记录日志到控制台
   */
  logToConsole(level, message, meta = {}) {
    if (!this.enableConsole) return;

    const logData = this.formatMessage(level, message, meta);
    const logString = `[${logData.timestamp}] ${logData.level} [${logData.service}] ${message}`;
    
    switch (level) {
      case LOG_LEVELS.ERROR:
        console.error(logString, meta);
        break;
      case LOG_LEVELS.WARN:
        console.warn(logString, meta);
        break;
      case LOG_LEVELS.INFO:
        console.info(logString, meta);
        break;
      case LOG_LEVELS.DEBUG:
        console.debug(logString, meta);
        break;
      default:
        console.log(logString, meta);
    }
  }

  /**
   * 记录日志到Analytics Engine
   */
  async logToAnalytics(level, message, meta = {}) {
    if (!this.enableAnalytics || !this.env.ANALYTICS_ENGINE) return;

    try {
      const logData = this.formatMessage(level, message, meta);
      
      await this.env.ANALYTICS_ENGINE.writeDataPoint({
        doubles: [level, Date.now()],
        blobs: [logData.message, JSON.stringify(logData.meta)],
        indexes: [logData.service, logData.environment]
      });
    } catch (error) {
      console.error('Failed to log to Analytics Engine:', error);
    }
  }

  /**
   * 记录日志到KV存储
   */
  async logToKV(level, message, meta = {}) {
    if (!this.enableKV || !this.env.LOGS_KV) return;

    try {
      const logData = this.formatMessage(level, message, meta);
      const key = `logs:${this.service}:${this.environment}:${Date.now()}:${crypto.randomUUID()}`;
      
      await this.env.LOGS_KV.put(key, JSON.stringify(logData), {
        expirationTtl: 7 * 24 * 60 * 60 // 7天过期
      });
    } catch (error) {
      console.error('Failed to log to KV:', error);
    }
  }

  /**
   * 主要日志记录方法
   */
  async log(level, message, meta = {}) {
    if (level > this.level) return;

    // 并行记录到多个目标
    const promises = [
      this.logToConsole(level, message, meta),
      this.logToAnalytics(level, message, meta),
      this.logToKV(level, message, meta)
    ];

    try {
      await Promise.all(promises);
    } catch (error) {
      console.error('Logging error:', error);
    }
  }

  /**
   * 错误日志
   */
  async error(message, meta = {}) {
    await this.log(LOG_LEVELS.ERROR, message, meta);
  }

  /**
   * 警告日志
   */
  async warn(message, meta = {}) {
    await this.log(LOG_LEVELS.WARN, message, meta);
  }

  /**
   * 信息日志
   */
  async info(message, meta = {}) {
    await this.log(LOG_LEVELS.INFO, message, meta);
  }

  /**
   * 调试日志
   */
  async debug(message, meta = {}) {
    await this.log(LOG_LEVELS.DEBUG, message, meta);
  }
}

/**
 * 请求日志中间件
 */
export function createLoggerMiddleware(env, options = {}) {
  const logger = new WorkersLogger(env, options);

  return async (c, next) => {
    const start = Date.now();
    const requestId = crypto.randomUUID();
    
    // 获取请求信息
    const url = new URL(c.req.url);
    const method = c.req.method;
    const path = url.pathname;
    const userAgent = c.req.header('User-Agent') || 'unknown';
    const ip = c.req.header('CF-Connecting-IP') || c.req.header('X-Forwarded-For') || 'unknown';
    
    // 设置请求ID到上下文
    c.set('requestId', requestId);
    c.set('logger', logger);

    // 记录请求开始
    await logger.info('Request started', {
      requestId,
      method,
      path,
      userAgent,
      ip,
      query: Object.fromEntries(url.searchParams)
    });

    try {
      await next();
      
      const duration = Date.now() - start;
      const status = c.res.status;
      
      // 记录响应信息
      await logger.info('Request completed', {
        requestId,
        method,
        path,
        status,
        duration,
        userAgent,
        ip
      });

      // 慢请求警告
      if (duration > 5000) {
        await logger.warn('Slow request detected', {
          requestId,
          method,
          path,
          duration,
          status
        });
      }

      // 错误响应记录
      if (status >= 400) {
        await logger.warn('Request returned error status', {
          requestId,
          method,
          path,
          status,
          duration
        });
      }

    } catch (error) {
      const duration = Date.now() - start;
      
      // 记录异常
      await logger.error('Request failed with exception', {
        requestId,
        method,
        path,
        duration,
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name
        },
        userAgent,
        ip
      });

      // 重新抛出错误让错误处理中间件处理
      throw error;
    }
  };
}

/**
 * 错误日志记录器
 */
export async function logError(logger, error, context = {}) {
  const errorInfo = {
    message: error.message,
    stack: error.stack,
    name: error.name,
    code: error.code || 'UNKNOWN_ERROR'
  };

  await logger.error('Application error occurred', {
    ...context,
    error: errorInfo,
    timestamp: new Date().toISOString()
  });
}

/**
 * 性能监控中间件
 */
export function createPerformanceMiddleware(env) {
  const logger = new WorkersLogger(env, { 
    service: 'performance-monitor',
    level: LOG_LEVELS.INFO 
  });

  return async (c, next) => {
    const start = Date.now();
    const requestId = c.get('requestId') || crypto.randomUUID();
    
    try {
      await next();
      
      const duration = Date.now() - start;
      
      // 记录性能指标
      if (c.env.ANALYTICS_ENGINE) {
        await c.env.ANALYTICS_ENGINE.writeDataPoint({
          doubles: [duration, c.res.status],
          blobs: [c.req.method, new URL(c.req.url).pathname],
          indexes: ['performance', 'api']
        });
      }

      // 性能警告
      if (duration > 1000) {
        await logger.warn('Performance degradation detected', {
          requestId,
          method: c.req.method,
          path: new URL(c.req.url).pathname,
          duration,
          status: c.res.status
        });
      }

    } catch (error) {
      const duration = Date.now() - start;
      
      await logger.error('Request failed with performance impact', {
        requestId,
        method: c.req.method,
        path: new URL(c.req.url).pathname,
        duration,
        error: {
          message: error.message,
          stack: error.stack
        }
      });

      throw error;
    }
  };
}

/**
 * 安全日志记录器
 */
export function createSecurityLogger(env) {
  const logger = new WorkersLogger(env, { 
    service: 'security-monitor',
    level: LOG_LEVELS.WARN 
  });

  return {
    /**
     * 记录认证失败
     */
    async logAuthFailure(ip, username, reason) {
      await logger.warn('Authentication failure', {
        ip,
        username,
        reason,
        timestamp: new Date().toISOString()
      });
    },

    /**
     * 记录可疑活动
     */
    async logSuspiciousActivity(ip, activity, details = {}) {
      await logger.warn('Suspicious activity detected', {
        ip,
        activity,
        details,
        timestamp: new Date().toISOString()
      });
    },

    /**
     * 记录权限拒绝
     */
    async logPermissionDenied(userId, action, resource) {
      await logger.warn('Permission denied', {
        userId,
        action,
        resource,
        timestamp: new Date().toISOString()
      });
    }
  };
}

/**
 * 日志查询工具
 */
export class LogQuery {
  constructor(env) {
    this.env = env;
  }

  /**
   * 从KV存储查询日志
   */
  async queryLogs(options = {}) {
    const {
      service = 'maimai-note-pad',
      environment = 'production',
      level,
      startTime,
      endTime,
      limit = 100
    } = options;

    if (!this.env.LOGS_KV) {
      throw new Error('Logs KV namespace not configured');
    }

    const prefix = `logs:${service}:${environment}:`;
    const logs = [];
    
    try {
      const list = await this.env.LOGS_KV.list({ prefix, limit });
      
      for (const key of list.keys) {
        const logData = await this.env.LOGS_KV.get(key.name, 'json');
        
        if (logData) {
          const timestamp = new Date(logData.timestamp);
          
          // 时间过滤
          if (startTime && timestamp < new Date(startTime)) continue;
          if (endTime && timestamp > new Date(endTime)) continue;
          
          // 级别过滤
          if (level && logData.level !== level) continue;
          
          logs.push(logData);
        }
      }
      
      return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    } catch (error) {
      console.error('Failed to query logs:', error);
      throw error;
    }
  }
}