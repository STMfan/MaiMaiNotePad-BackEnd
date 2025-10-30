/**
 * Cloudflare Workers Rate Limiting Middleware
 * Rate limiting implementation for Cloudflare Workers
 */

import { HTTPException } from 'hono/http-exception';

/**
 * Rate limiter configuration
 */
const RATE_LIMIT_CONFIG = {
  // Default limits
  DEFAULT_LIMITS: {
    windowMs: 60 * 1000, // 1 minute
    max: 100, // 100 requests per minute
    message: 'Too many requests from this IP, please try again later.',
    standardHeaders: true,
    legacyHeaders: false,
    skipFailedRequests: false,
    skipSuccessfulRequests: false
  },
  
  // Endpoint specific limits
  ENDPOINT_LIMITS: {
    '/api/auth/login': {
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 10, // 10 attempts per 15 minutes
      message: 'Too many login attempts, please try again later.'
    },
    '/api/auth/register': {
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 5, // 5 registrations per hour
      message: 'Registration limit exceeded, please try again later.'
    },
    '/api/auth/refresh': {
      windowMs: 60 * 1000, // 1 minute
      max: 30, // 30 refresh attempts per minute
      message: 'Too many token refresh attempts.'
    },
    '/api/files/upload': {
      windowMs: 60 * 1000, // 1 minute
      max: 20, // 20 uploads per minute
      message: 'Upload limit exceeded, please try again later.'
    },
    '/api/admin': {
      windowMs: 60 * 1000, // 1 minute
      max: 50, // 50 admin requests per minute
      message: 'Admin request limit exceeded.'
    }
  },
  
  // IP whitelist (bypass rate limiting)
  IP_WHITELIST: [
    '127.0.0.1',
    '::1',
    'localhost'
  ],
  
  // User whitelist (bypass rate limiting)
  USER_WHITELIST: []
};

/**
 * Rate limiter using KV storage
 */
class RateLimiter {
  constructor(env, config = {}) {
    this.env = env;
    this.config = { ...RATE_LIMIT_CONFIG.DEFAULT_LIMITS, ...config };
    this.kv = env.MAIMAI_KV || env.RATE_LIMIT_KV;
  }

  /**
   * Get client identifier (IP or user ID)
   * @param {Object} c - Hono context
   * @returns {string} Client identifier
   */
  getClientId(c) {
    // Try to get user ID from auth context
    const user = c.get('user');
    if (user?.userId) {
      return `user:${user.userId}`;
    }
    
    // Fall back to IP address
    const cfConnectingIp = c.req.header('cf-connecting-ip');
    const xForwardedFor = c.req.header('x-forwarded-for');
    const xRealIp = c.req.header('x-real-ip');
    
    return cfConnectingIp || xForwardedFor?.split(',')[0]?.trim() || xRealIp || 'unknown';
  }

  /**
   * Check if client is whitelisted
   * @param {string} clientId - Client identifier
   * @returns {boolean} Is whitelisted
   */
  isWhitelisted(clientId) {
    // Check IP whitelist
    if (clientId.includes('.')) {
      return RATE_LIMIT_CONFIG.IP_WHITELIST.includes(clientId);
    }
    
    // Check user whitelist
    if (clientId.startsWith('user:')) {
      const userId = clientId.replace('user:', '');
      return RATE_LIMIT_CONFIG.USER_WHITELIST.includes(userId);
    }
    
    return false;
  }

  /**
   * Get rate limit key
   * @param {string} clientId - Client identifier
   * @param {string} endpoint - Endpoint path
   * @returns {string} Rate limit key
   */
  getRateLimitKey(clientId, endpoint) {
    const windowStart = Math.floor(Date.now() / this.config.windowMs);
    return `rate_limit:${clientId}:${endpoint}:${windowStart}`;
  }

  /**
   * Get current request count
   * @param {string} key - Rate limit key
   * @returns {Promise<number>} Request count
   */
  async getCurrentCount(key) {
    if (!this.kv) return 0;
    
    try {
      const count = await this.kv.get(key);
      return count ? parseInt(count) : 0;
    } catch (error) {
      console.error('Error getting rate limit count:', error);
      return 0;
    }
  }

  /**
   * Increment request count
   * @param {string} key - Rate limit key
   * @param {number} ttl - Time to live in seconds
   */
  async incrementCount(key, ttl) {
    if (!this.kv) return;
    
    try {
      const currentCount = await this.getCurrentCount(key);
      const newCount = currentCount + 1;
      
      await this.kv.put(key, newCount.toString(), {
        expirationTtl: ttl
      });
      
      return newCount;
    } catch (error) {
      console.error('Error incrementing rate limit count:', error);
      return 1;
    }
  }

  /**
   * Check rate limit
   * @param {Object} c - Hono context
   * @returns {Promise<Object>} Rate limit result
   */
  async checkRateLimit(c) {
    const clientId = this.getClientId(c);
    const endpoint = c.req.path;
    
    // Check whitelist
    if (this.isWhitelisted(clientId)) {
      return {
        allowed: true,
        limit: this.config.max,
        remaining: this.config.max,
        reset: new Date(Date.now() + this.config.windowMs)
      };
    }
    
    // Get endpoint-specific config
    const endpointConfig = this.getEndpointConfig(endpoint);
    const key = this.getRateLimitKey(clientId, endpoint);
    
    const currentCount = await this.getCurrentCount(key);
    const remaining = Math.max(0, endpointConfig.max - currentCount);
    const resetTime = new Date(Date.now() + endpointConfig.windowMs);
    
    if (currentCount >= endpointConfig.max) {
      return {
        allowed: false,
        limit: endpointConfig.max,
        remaining: 0,
        reset: resetTime,
        message: endpointConfig.message
      };
    }
    
    // Increment count
    const ttl = Math.ceil(endpointConfig.windowMs / 1000);
    await this.incrementCount(key, ttl);
    
    return {
      allowed: true,
      limit: endpointConfig.max,
      remaining: remaining - 1,
      reset: resetTime
    };
  }

  /**
   * Get endpoint-specific configuration
   * @param {string} endpoint - Endpoint path
   * @returns {Object} Endpoint configuration
   */
  getEndpointConfig(endpoint) {
    // Check for exact matches first
    if (RATE_LIMIT_CONFIG.ENDPOINT_LIMITS[endpoint]) {
      return { ...this.config, ...RATE_LIMIT_CONFIG.ENDPOINT_LIMITS[endpoint] };
    }
    
    // Check for prefix matches
    for (const [prefix, config] of Object.entries(RATE_LIMIT_CONFIG.ENDPOINT_LIMITS)) {
      if (endpoint.startsWith(prefix)) {
        return { ...this.config, ...config };
      }
    }
    
    return this.config;
  }

  /**
   * Add rate limit headers to response
   * @param {Object} c - Hono context
   * @param {Object} rateLimitInfo - Rate limit information
   */
  addRateLimitHeaders(c, rateLimitInfo) {
    if (this.config.standardHeaders) {
      c.header('X-RateLimit-Limit', rateLimitInfo.limit.toString());
      c.header('X-RateLimit-Remaining', rateLimitInfo.remaining.toString());
      c.header('X-RateLimit-Reset', rateLimitInfo.reset.toISOString());
    }
    
    if (this.config.legacyHeaders) {
      c.header('X-Rate-Limit-Limit', rateLimitInfo.limit.toString());
      c.header('X-Rate-Limit-Remaining', rateLimitInfo.remaining.toString());
      c.header('X-Rate-Limit-Reset', rateLimitInfo.reset.toString());
    }
  }
}

/**
 * Create rate limiting middleware
 * @param {Object} env - Environment variables
 * @param {Object} options - Rate limit options
 * @returns {Function} Rate limiting middleware
 */
export function createRateLimitMiddleware(env, options = {}) {
  const rateLimiter = new RateLimiter(env, options);
  
  return async function rateLimitMiddleware(c, next) {
    try {
      const rateLimitInfo = await rateLimiter.checkRateLimit(c);
      
      // Add rate limit headers
      rateLimiter.addRateLimitHeaders(c, rateLimitInfo);
      
      if (!rateLimitInfo.allowed) {
        throw new HTTPException(429, { 
          message: rateLimitInfo.message || 'Too many requests',
          res: c.json({
            error: 'Rate limit exceeded',
            message: rateLimitInfo.message,
            retryAfter: Math.ceil((rateLimitInfo.reset - new Date()) / 1000)
          }, 429)
        });
      }
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      console.error('Rate limit middleware error:', error);
      throw new HTTPException(500, { 
        message: 'Rate limiting error',
        res: c.json({ error: 'Internal server error' }, 500)
      });
    }
  };
}

/**
 * Create endpoint-specific rate limiting middleware
 * @param {Object} env - Environment variables
 * @param {Object} config - Custom rate limit configuration
 * @returns {Function} Rate limiting middleware
 */
export function createEndpointRateLimit(env, config) {
  const rateLimiter = new RateLimiter(env, config);
  
  return async function endpointRateLimitMiddleware(c, next) {
    try {
      const rateLimitInfo = await rateLimiter.checkRateLimit(c);
      
      // Add rate limit headers
      rateLimiter.addRateLimitHeaders(c, rateLimitInfo);
      
      if (!rateLimitInfo.allowed) {
        throw new HTTPException(429, { 
          message: rateLimitInfo.message || 'Too many requests',
          res: c.json({
            error: 'Rate limit exceeded',
            message: rateLimitInfo.message,
            retryAfter: Math.ceil((rateLimitInfo.reset - new Date()) / 1000)
          }, 429)
        });
      }
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      console.error('Endpoint rate limit error:', error);
      throw new HTTPException(500, { 
        message: 'Rate limiting error',
        res: c.json({ error: 'Internal server error' }, 500)
      });
    }
  };
}