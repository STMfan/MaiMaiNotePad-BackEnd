/**
 * Cloudflare Workers Authentication Middleware
 * Authentication and authorization middleware for Cloudflare Workers
 */

import { HTTPException } from 'hono/http-exception';
import { jwt } from 'hono/jwt';

/**
 * JWT configuration
 */
const JWT_CONFIG = {
  SECRET: process.env.JWT_SECRET || 'your-secret-key-change-in-production',
  ALGORITHM: 'HS256',
  EXPIRES_IN: '24h',
  REFRESH_EXPIRES_IN: '7d'
};

/**
 * Authentication middleware
 */
export class AuthMiddleware {
  constructor(env) {
    this.env = env;
    this.jwtSecret = env.JWT_SECRET || JWT_CONFIG.SECRET;
  }

  /**
   * Verify JWT token
   * @param {string} token - JWT token
   * @returns {Promise<Object>} Decoded token payload
   */
  async verifyToken(token) {
    try {
      const secret = this.jwtSecret;
      const payload = await jwt.verify(token, secret, {
        algorithms: [JWT_CONFIG.ALGORITHM]
      });
      
      return payload;
    } catch (error) {
      throw new HTTPException(401, {
        message: 'Invalid or expired token',
        res: new Response(JSON.stringify({
          error: 'Unauthorized',
          message: 'Invalid or expired token'
        }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        })
      });
    }
  }

  /**
   * Generate JWT token
   * @param {Object} payload - Token payload
   * @param {string} expiresIn - Token expiration time
   * @returns {string} JWT token
   */
  generateToken(payload, expiresIn = JWT_CONFIG.EXPIRES_IN) {
    const secret = this.jwtSecret;
    return jwt.sign(payload, secret, {
      algorithm: JWT_CONFIG.ALGORITHM,
      expiresIn
    });
  }

  /**
   * Extract token from request
   * @param {Object} c - Hono context
   * @returns {string|null} Extracted token
   */
  extractToken(c) {
    // Check Authorization header
    const authHeader = c.req.header('Authorization');
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }
    
    // Check API key header
    const apiKey = c.req.header('X-API-Key');
    if (apiKey) {
      return apiKey;
    }
    
    // Check query parameter
    const url = new URL(c.req.url);
    const tokenParam = url.searchParams.get('token');
    if (tokenParam) {
      return tokenParam;
    }
    
    return null;
  }

  /**
   * Main authentication middleware
   * @param {Object} c - Hono context
   * @param {Function} next - Next middleware
   */
  async authenticate(c, next) {
    try {
      const token = this.extractToken(c);
      
      if (!token) {
        throw new HTTPException(401, {
          message: 'No token provided',
          res: new Response(JSON.stringify({
            error: 'Unauthorized',
            message: 'No authentication token provided'
          }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
      
      // Verify token
      const payload = await this.verifyToken(token);
      
      // Add user info to context
      c.set('user', payload);
      c.set('userId', payload.userId);
      c.set('token', token);
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      throw new HTTPException(401, {
        message: 'Authentication failed',
        res: new Response(JSON.stringify({
          error: 'Unauthorized',
          message: 'Authentication failed'
        }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        })
      });
    }
  }

  /**
   * Optional authentication middleware (doesn't fail if no token)
   * @param {Object} c - Hono context
   * @param {Function} next - Next middleware
   */
  async optionalAuthenticate(c, next) {
    try {
      const token = this.extractToken(c);
      
      if (token) {
        const payload = await this.verifyToken(token);
        c.set('user', payload);
        c.set('userId', payload.userId);
        c.set('token', token);
      }
      
      await next();
      
    } catch (error) {
      // Ignore authentication errors for optional auth
      await next();
    }
  }

  /**
   * API key authentication middleware
   * @param {Object} c - Hono context
   * @param {Function} next - Next middleware
   */
  async apiKeyAuth(c, next) {
    try {
      const apiKey = c.req.header('X-API-Key');
      
      if (!apiKey) {
        throw new HTTPException(401, {
          message: 'No API key provided',
          res: new Response(JSON.stringify({
            error: 'Unauthorized',
            message: 'No API key provided'
          }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
      
      // Validate API key (implement your validation logic)
      const isValid = await this.validateApiKey(apiKey);
      
      if (!isValid) {
        throw new HTTPException(401, {
          message: 'Invalid API key',
          res: new Response(JSON.stringify({
            error: 'Unauthorized',
            message: 'Invalid API key'
          }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
      
      // Add API key info to context
      c.set('apiKey', apiKey);
      c.set('isApiKey', true);
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      throw new HTTPException(401, {
        message: 'API key authentication failed',
        res: new Response(JSON.stringify({
          error: 'Unauthorized',
          message: 'API key authentication failed'
        }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        })
      });
    }
  }

  /**
   * Validate API key
   * @param {string} apiKey - API key to validate
   * @returns {Promise<boolean>} Validation result
   */
  async validateApiKey(apiKey) {
    // Implement your API key validation logic here
    // This could check against a database, KV store, or environment variables
    
    if (!this.env.API_KEYS) {
      return false;
    }
    
    // Check if API key exists in environment
    const validKeys = this.env.API_KEYS.split(',').map(key => key.trim());
    return validKeys.includes(apiKey);
  }

  /**
   * Role-based authorization middleware
   * @param {string[]} allowedRoles - Allowed roles
   * @returns {Function} Authorization middleware
   */
  authorizeRoles(allowedRoles) {
    return async (c, next) => {
      try {
        const user = c.get('user');
        
        if (!user) {
          throw new HTTPException(401, {
            message: 'User not authenticated',
            res: new Response(JSON.stringify({
              error: 'Unauthorized',
              message: 'User not authenticated'
            }), {
              status: 401,
              headers: { 'Content-Type': 'application/json' }
            })
          });
        }
        
        const userRole = user.role || 'user';
        
        if (!allowedRoles.includes(userRole)) {
          throw new HTTPException(403, {
            message: 'Insufficient permissions',
            res: new Response(JSON.stringify({
              error: 'Forbidden',
              message: 'Insufficient permissions'
            }), {
              status: 403,
              headers: { 'Content-Type': 'application/json' }
            })
          });
        }
        
        await next();
        
      } catch (error) {
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(403, {
          message: 'Authorization failed',
          res: new Response(JSON.stringify({
            error: 'Forbidden',
            message: 'Authorization failed'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
    };
  }

  /**
   * Permission-based authorization middleware
   * @param {string[]} requiredPermissions - Required permissions
   * @returns {Function} Authorization middleware
   */
  authorizePermissions(requiredPermissions) {
    return async (c, next) => {
      try {
        const user = c.get('user');
        
        if (!user) {
          throw new HTTPException(401, {
            message: 'User not authenticated',
            res: new Response(JSON.stringify({
              error: 'Unauthorized',
              message: 'User not authenticated'
            }), {
              status: 401,
              headers: { 'Content-Type': 'application/json' }
            })
          });
        }
        
        const userPermissions = user.permissions || [];
        
        // Check if user has all required permissions
        const hasAllPermissions = requiredPermissions.every(permission =>
          userPermissions.includes(permission)
        );
        
        if (!hasAllPermissions) {
          throw new HTTPException(403, {
            message: 'Insufficient permissions',
            res: new Response(JSON.stringify({
              error: 'Forbidden',
              message: 'Insufficient permissions'
            }), {
              status: 403,
              headers: { 'Content-Type': 'application/json' }
            })
          });
        }
        
        await next();
        
      } catch (error) {
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(403, {
          message: 'Authorization failed',
          res: new Response(JSON.stringify({
            error: 'Forbidden',
            message: 'Authorization failed'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
    };
  }

  /**
   * Admin authorization middleware
   * @param {Object} c - Hono context
   * @param {Function} next - Next middleware
   */
  async authorizeAdmin(c, next) {
    try {
      const user = c.get('user');
      
      if (!user) {
        throw new HTTPException(401, {
          message: 'User not authenticated',
          res: new Response(JSON.stringify({
            error: 'Unauthorized',
            message: 'User not authenticated'
          }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
      
      const userRole = user.role || 'user';
      
      if (userRole !== 'admin' && userRole !== 'super_admin') {
        throw new HTTPException(403, {
          message: 'Admin access required',
          res: new Response(JSON.stringify({
            error: 'Forbidden',
            message: 'Admin access required'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          })
        });
      }
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      throw new HTTPException(403, {
        message: 'Admin authorization failed',
        res: new Response(JSON.stringify({
          error: 'Forbidden',
          message: 'Admin authorization failed'
        }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' }
        })
      });
    }
  }

  /**
   * Rate limiting for authentication endpoints
   * @param {Object} c - Hono context
   * @param {Function} next - Next middleware
   */
  async authRateLimit(c, next) {
    try {
      const clientId = this.getClientIdentifier(c);
      const key = `auth_attempts:${clientId}`;
      
      // Get current attempts
      const attempts = await this.env.MAIMAI_KV?.get(key) || '0';
      const currentAttempts = parseInt(attempts);
      
      // Check if limit exceeded (5 attempts per 15 minutes)
      if (currentAttempts >= 5) {
        throw new HTTPException(429, {
          message: 'Too many authentication attempts',
          res: new Response(JSON.stringify({
            error: 'Too Many Requests',
            message: 'Too many authentication attempts. Please try again later.',
            retryAfter: 900 // 15 minutes
          }), {
            status: 429,
            headers: { 
              'Content-Type': 'application/json',
              'Retry-After': '900'
            }
          })
        });
      }
      
      // Increment attempts
      const newAttempts = currentAttempts + 1;
      await this.env.MAIMAI_KV?.put(key, newAttempts.toString(), {
        expirationTtl: 900 // 15 minutes
      });
      
      await next();
      
    } catch (error) {
      if (error instanceof HTTPException) {
        throw error;
      }
      
      throw new HTTPException(429, {
        message: 'Authentication rate limit error',
        res: new Response(JSON.stringify({
          error: 'Too Many Requests',
          message: 'Authentication rate limit error'
        }), {
          status: 429,
          headers: { 'Content-Type': 'application/json' }
        })
      });
    }
  }

  /**
   * Get client identifier for rate limiting
   * @param {Object} c - Hono context
   * @returns {string} Client identifier
   */
  getClientIdentifier(c) {
    const cf = c.req.raw.cf;
    const ip = cf?.ip || c.req.header('CF-Connecting-IP') || c.req.header('X-Forwarded-For') || 'unknown';
    const userAgent = c.req.header('User-Agent') || 'unknown';
    
    // Simple hash function for client identification
    const str = `${ip}:${userAgent}`;
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    
    return Math.abs(hash).toString(36);
  }
}

/**
 * Create authentication middleware
 * @param {Object} env - Environment variables
 * @returns {Object} Authentication middleware functions
 */
export function createAuthMiddleware(env) {
  const authMiddleware = new AuthMiddleware(env);
  
  return {
    authenticate: authMiddleware.authenticate.bind(authMiddleware),
    optionalAuthenticate: authMiddleware.optionalAuthenticate.bind(authMiddleware),
    apiKeyAuth: authMiddleware.apiKeyAuth.bind(authMiddleware),
    authorizeRoles: authMiddleware.authorizeRoles.bind(authMiddleware),
    authorizePermissions: authMiddleware.authorizePermissions.bind(authMiddleware),
    authorizeAdmin: authMiddleware.authorizeAdmin.bind(authMiddleware),
    authRateLimit: authMiddleware.authRateLimit.bind(authMiddleware),
    generateToken: authMiddleware.generateToken.bind(authMiddleware),
    verifyToken: authMiddleware.verifyToken.bind(authMiddleware)
  };
}