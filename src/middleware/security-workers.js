/**
 * Cloudflare Workers Security Middleware
 * Security headers, CORS, and protection middleware for Cloudflare Workers
 */

/**
 * Security configuration
 */
const SECURITY_CONFIG = {
  // CORS configuration
  CORS: {
    ALLOWED_ORIGINS: ['*'], // Will be overridden by env config
    ALLOWED_METHODS: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    ALLOWED_HEADERS: [
      'Content-Type',
      'Authorization',
      'X-API-Key',
      'X-Requested-With',
      'X-CSRF-Token',
      'Accept',
      'Accept-Language',
      'Accept-Encoding',
      'Origin',
      'Referer',
      'User-Agent'
    ],
    EXPOSED_HEADERS: ['X-Total-Count', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'],
    CREDENTIALS: true,
    MAX_AGE: 86400 // 24 hours
  },
  
  // Security headers
  HEADERS: {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'"
  },
  
  // Rate limiting
  RATE_LIMIT: {
    WINDOW_MS: 15 * 60 * 1000, // 15 minutes
    MAX_REQUESTS: 100,
    SKIP_SUCCESSFUL_REQUESTS: false
  },
  
  // Request size limits
  REQUEST_LIMITS: {
    MAX_BODY_SIZE: 10 * 1024 * 1024, // 10MB
    MAX_URL_LENGTH: 2048,
    MAX_HEADER_SIZE: 8192
  }
};

/**
 * Security middleware class
 */
export class SecurityMiddleware {
  constructor(config = {}) {
    this.config = { ...SECURITY_CONFIG, ...config };
  }

  /**
   * CORS handler
   * @param {Request} request - Request object
   * @returns {Object} CORS result
   */
  handleCors(request) {
    const origin = request.headers.get('Origin');
    const allowedOrigins = this.config.CORS.ALLOWED_ORIGINS;
    
    // Check if origin is allowed
    let allowedOrigin = allowedOrigins.includes('*') ? '*' : null;
    if (origin && allowedOrigins.includes(origin)) {
      allowedOrigin = origin;
    }
    
    // Handle preflight requests
    if (request.method === 'OPTIONS') {
      const headers = new Headers({
        'Access-Control-Allow-Methods': this.config.CORS.ALLOWED_METHODS.join(', '),
        'Access-Control-Allow-Headers': this.config.CORS.ALLOWED_HEADERS.join(', '),
        'Access-Control-Max-Age': this.config.CORS.MAX_AGE.toString(),
        'Access-Control-Allow-Credentials': this.config.CORS.CREDENTIALS.toString()
      });
      
      if (allowedOrigin) {
        headers.set('Access-Control-Allow-Origin', allowedOrigin);
      }
      
      return {
        isPreflight: true,
        headers,
        allowedOrigin
      };
    }
    
    return {
      isPreflight: false,
      allowedOrigin
    };
  }

  /**
   * Validate request size limits
   * @param {Request} request - Request object
   * @returns {Object} Validation result
   */
  validateRequestSize(request) {
    // Check URL length
    const url = request.url;
    if (url.length > this.config.REQUEST_LIMITS.MAX_URL_LENGTH) {
      return {
        valid: false,
        status: 414,
        message: 'Request URL is too long'
      };
    }
    
    // Check header size
    let headerSize = 0;
    for (const [key, value] of request.headers.entries()) {
      headerSize += key.length + value.length;
    }
    
    if (headerSize > this.config.REQUEST_LIMITS.MAX_HEADER_SIZE) {
      return {
        valid: false,
        status: 431,
        message: 'Request headers are too large'
      };
    }
    
    return { valid: true };
  }

  /**
   * Add security headers to response
   * @param {Response} response - Response object
   * @returns {Response} Response with security headers
   */
  addSecurityHeaders(response, corsData = {}) {
    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: new Headers(response.headers)
    });
    
    // Add CORS headers if available
    if (corsData.allowedOrigin) {
      newResponse.headers.set('Access-Control-Allow-Origin', corsData.allowedOrigin);
      newResponse.headers.set('Access-Control-Allow-Credentials', this.config.CORS.CREDENTIALS.toString());
      newResponse.headers.set('Access-Control-Expose-Headers', this.config.CORS.EXPOSED_HEADERS.join(', '));
    }
    
    // Add security headers
    Object.entries(this.config.HEADERS).forEach(([key, value]) => {
      newResponse.headers.set(key, value);
    });
    
    // Remove server identification headers
    newResponse.headers.delete('Server');
    newResponse.headers.delete('X-Powered-By');
    
    return newResponse;
  }

  /**
   * Main security middleware function
   * @param {Request} request - Request object
   * @returns {Object} Security result
   */
  processRequest(request) {
    // Handle CORS
    const corsResult = this.handleCors(request);
    if (corsResult.isPreflight) {
      return {
        shouldContinue: false,
        response: new Response(null, {
          status: 204,
          headers: corsResult.headers
        })
      };
    }
    
    // Validate request size
    const sizeValidation = this.validateRequestSize(request);
    if (!sizeValidation.valid) {
      return {
        shouldContinue: false,
        response: new Response(JSON.stringify({
          error: sizeValidation.message
        }), {
          status: sizeValidation.status,
          headers: { 'Content-Type': 'application/json' }
        })
      };
    }
    
    return {
      shouldContinue: true,
      corsData: corsResult
    };
  }
}

/**
 * Create security middleware
 * @param {Object} config - Configuration object
 * @returns {Function} Security middleware function
 */
export function createSecurityMiddleware(config = {}) {
  const securityMiddleware = new SecurityMiddleware(config);
  
  return async (request, env) => {
    // Update config with environment-specific settings
    if (env.ALLOWED_ORIGINS) {
      securityMiddleware.config.CORS.ALLOWED_ORIGINS = env.ALLOWED_ORIGINS.split(',');
    }
    
    const result = securityMiddleware.processRequest(request);
    
    if (!result.shouldContinue) {
      return result.response;
    }
    
    // Store CORS data for response processing
    request.securityContext = {
      corsData: result.corsData
    };
    
    return null; // Continue to next middleware
  };
}