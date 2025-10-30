/**
 * Logger Utility for Cloudflare Workers
 * Provides structured logging with different levels and outputs
 */

/**
 * Log levels hierarchy
 */
const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

/**
 * Logger class
 */
class Logger {
  constructor(options = {}) {
    this.level = options.level || 'info';
    this.service = options.service || 'maimai-backend';
    this.environment = options.environment || 'development';
    this.enableConsole = options.enableConsole !== false;
    this.enableStructured = options.enableStructured !== false;
  }

  /**
   * Check if log level should be logged
   * @param {string} level - Log level to check
   * @returns {boolean} Whether to log
   */
  shouldLog(level) {
    return LOG_LEVELS[level] <= LOG_LEVELS[this.level];
  }

  /**
   * Format log message
   * @param {string} level - Log level
   * @param {string} message - Log message
   * @param {Object} meta - Metadata
   * @returns {Object} Formatted log
   */
  formatLog(level, message, meta = {}) {
    const timestamp = new Date().toISOString();
    
    const logEntry = {
      timestamp,
      level: level.toUpperCase(),
      service: this.service,
      environment: this.environment,
      message,
      ...meta
    };

    // Add request context if available
    if (meta.requestId) {
      logEntry.requestId = meta.requestId;
    }

    return logEntry;
  }

  /**
   * Log to console
   * @param {Object} logEntry - Log entry
   */
  logToConsole(logEntry) {
    if (!this.enableConsole) return;

    const { timestamp, level, message, ...meta } = logEntry;
    const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
    
    const logMessage = `[${timestamp}] [${level}] ${message}${metaStr}`;

    switch (logEntry.level.toLowerCase()) {
      case 'error':
        console.error(logMessage);
        break;
      case 'warn':
        console.warn(logMessage);
        break;
      case 'debug':
        console.debug(logMessage);
        break;
      default:
        console.log(logMessage);
    }
  }

  /**
   * Create child logger with additional context
   * @param {Object} context - Context to add
   * @returns {Logger} Child logger
   */
  child(context) {
    const childLogger = new Logger({
      level: this.level,
      service: this.service,
      environment: this.environment,
      enableConsole: this.enableConsole,
      enableStructured: this.enableStructured
    });

    // Store context for future logs
    childLogger.context = { ...this.context, ...context };
    
    return childLogger;
  }

  /**
   * Log error message
   * @param {string} message - Error message
   * @param {Object} meta - Metadata
   */
  error(message, meta = {}) {
    if (!this.shouldLog('error')) return;

    const logEntry = this.formatLog('error', message, { ...this.context, ...meta });
    this.logToConsole(logEntry);
    
    // In production, you might want to send to external logging service
    if (this.environment === 'production') {
      // TODO: Send to logging service (e.g., Sentry, Logtail, etc.)
    }
  }

  /**
   * Log warning message
   * @param {string} message - Warning message
   * @param {Object} meta - Metadata
   */
  warn(message, meta = {}) {
    if (!this.shouldLog('warn')) return;

    const logEntry = this.formatLog('warn', message, { ...this.context, ...meta });
    this.logToConsole(logEntry);
  }

  /**
   * Log info message
   * @param {string} message - Info message
   * @param {Object} meta - Metadata
   */
  info(message, meta = {}) {
    if (!this.shouldLog('info')) return;

    const logEntry = this.formatLog('info', message, { ...this.context, ...meta });
    this.logToConsole(logEntry);
  }

  /**
   * Log debug message
   * @param {string} message - Debug message
   * @param {Object} meta - Metadata
   */
  debug(message, meta = {}) {
    if (!this.shouldLog('debug')) return;

    const logEntry = this.formatLog('debug', message, { ...this.context, ...meta });
    this.logToConsole(logEntry);
  }
}

/**
 * Create logger instance
 * @param {Object} options - Logger options
 * @returns {Logger} Logger instance
 */
export function createLogger(options = {}) {
  return new Logger(options);
}

/**
 * Default logger instance
 */
export const logger = new Logger({
  level: 'info',
  service: 'maimai-backend',
  environment: 'development'
});

/**
 * Request logger middleware
 * @param {Request} request - Request object
 * @param {Object} env - Environment
 * @returns {Object} Logging context
 */
export function createRequestLogger(request, env) {
  const requestId = crypto.randomUUID();
  const startTime = Date.now();
  
  const context = {
    requestId,
    method: request.method,
    url: request.url,
    userAgent: request.headers.get('User-Agent'),
    ip: request.headers.get('CF-Connecting-IP')
  };

  const requestLogger = logger.child(context);
  
  // Log request start
  requestLogger.info('Request started', {
    headers: Object.fromEntries(request.headers.entries())
  });

  return {
    logger: requestLogger,
    requestId,
    logResponse: (response) => {
      const duration = Date.now() - startTime;
      requestLogger.info('Request completed', {
        status: response.status,
        duration: `${duration}ms`
      });
    },
    logError: (error) => {
      const duration = Date.now() - startTime;
      requestLogger.error('Request failed', {
        error: error.message,
        stack: error.stack,
        duration: `${duration}ms`
      });
    }
  };
}

/**
 * Performance logger
 * @param {string} operation - Operation name
 * @returns {Object} Performance logger
 */
export function createPerformanceLogger(operation) {
  const startTime = Date.now();
  const operationLogger = logger.child({ operation });
  
  operationLogger.info('Operation started');

  return {
    logComplete: (meta = {}) => {
      const duration = Date.now() - startTime;
      operationLogger.info('Operation completed', {
        duration: `${duration}ms`,
        ...meta
      });
    },
    logError: (error) => {
      const duration = Date.now() - startTime;
      operationLogger.error('Operation failed', {
        error: error.message,
        stack: error.stack,
        duration: `${duration}ms`
      });
    }
  };
}