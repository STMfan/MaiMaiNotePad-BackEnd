/**
 * Cloudflare Workers Cache Service
 * Distributed caching service using Cloudflare KV and in-memory caching
 */

import { HTTPException } from 'hono/http-exception';

/**
 * Cache Configuration
 */
const CACHE_CONFIG = {
  defaultTTL: 3600, // 1 hour
  maxKeyLength: 250,
  maxValueSize: 25 * 1024 * 1024, // 25MB (KV limit)
  compressionThreshold: 1024, // 1KB
  enableCompression: true,
  enableMetrics: true,
  namespace: 'maimai-cache'
};

/**
 * Cache Service Class
 */
export class CacheService {
  constructor(env) {
    this.env = env;
    this.localCache = new Map(); // In-memory cache for hot data
    this.metrics = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      errors: 0,
      totalRequests: 0
    };
  }

  /**
   * Get cache key with namespace
   * @param {string} key - Cache key
   * @param {string} prefix - Key prefix
   * @returns {string} Namespaced key
   */
  getNamespacedKey(key, prefix = '') {
    if (key.length > CACHE_CONFIG.maxKeyLength) {
      throw new HTTPException(400, { message: 'Cache key too long' });
    }
    
    const namespacedKey = `${CACHE_CONFIG.namespace}:${prefix}${key}`;
    return namespacedKey.slice(0, CACHE_CONFIG.maxKeyLength);
  }

  /**
   * Compress data
   * @param {*} data - Data to compress
   * @returns {Object} Compressed data
   */
  async compress(data) {
    if (!CACHE_CONFIG.enableCompression) {
      return { compressed: false, data };
    }

    try {
      const jsonStr = JSON.stringify(data);
      if (jsonStr.length < CACHE_CONFIG.compressionThreshold) {
        return { compressed: false, data };
      }

      // Simple compression using TextEncoder and gzip-like encoding
      const encoder = new TextEncoder();
      const uint8Array = encoder.encode(jsonStr);
      
      // For Cloudflare Workers, we can use Compression Streams API if available
      if (typeof CompressionStream !== 'undefined') {
        const stream = new CompressionStream('gzip');
        const writer = stream.writable.getWriter();
        writer.write(uint8Array);
        writer.close();
        
        const compressedData = new Response(stream.readable).arrayBuffer();
        return {
          compressed: true,
          data: Array.from(new Uint8Array(await compressedData)),
          originalSize: jsonStr.length,
          compressedSize: (await compressedData).byteLength
        };
      }

      return { compressed: false, data };
    } catch (error) {
      console.warn('Compression failed:', error);
      return { compressed: false, data };
    }
  }

  /**
   * Decompress data
   * @param {Object} compressedData - Compressed data
   * @returns {*} Decompressed data
   */
  async decompress(compressedData) {
    if (!compressedData.compressed) {
      return compressedData.data;
    }

    try {
      if (typeof DecompressionStream !== 'undefined') {
        const uint8Array = new Uint8Array(compressedData.data);
        const stream = new DecompressionStream('gzip');
        
        const writer = stream.writable.getWriter();
        writer.write(uint8Array);
        writer.close();
        
        const decompressedData = await new Response(stream.readable).text();
        return JSON.parse(decompressedData);
      }

      return compressedData.data;
    } catch (error) {
      console.warn('Decompression failed:', error);
      return compressedData.data;
    }
  }

  /**
   * Get value from cache
   * @param {string} key - Cache key
   * @param {Object} options - Cache options
   * @returns {*} Cached value
   */
  async get(key, options = {}) {
    this.metrics.totalRequests++;
    const namespacedKey = this.getNamespacedKey(key, options.prefix);

    try {
      // Check local cache first
      const localEntry = this.localCache.get(namespacedKey);
      if (localEntry && localEntry.expires > Date.now()) {
        this.metrics.hits++;
        return localEntry.data;
      } else if (localEntry) {
        this.localCache.delete(namespacedKey);
      }

      // Check KV store
      if (this.env.CACHE) {
        const cachedValue = await this.env.CACHE.get(namespacedKey, { type: 'json' });
        if (cachedValue !== null) {
          const decompressedValue = await this.decompress(cachedValue);
          
          // Store in local cache for faster access
          this.localCache.set(namespacedKey, {
            data: decompressedValue,
            expires: Date.now() + (options.ttl || CACHE_CONFIG.defaultTTL) * 1000
          });

          this.metrics.hits++;
          return decompressedValue;
        }
      }

      this.metrics.misses++;
      return null;
    } catch (error) {
      this.metrics.errors++;
      console.error('Cache get error:', error);
      return null;
    }
  }

  /**
   * Set value in cache
   * @param {string} key - Cache key
   * @param {*} value - Value to cache
   * @param {Object} options - Cache options
   * @returns {boolean} Success
   */
  async set(key, value, options = {}) {
    const namespacedKey = this.getNamespacedKey(key, options.prefix);
    const ttl = options.ttl || CACHE_CONFIG.defaultTTL;

    try {
      // Compress value if enabled
      const compressedValue = await this.compress(value);
      
      // Store in local cache
      this.localCache.set(namespacedKey, {
        data: compressedValue,
        expires: Date.now() + ttl * 1000
      });

      // Store in KV store
      if (this.env.CACHE) {
        // Check value size
        const valueSize = JSON.stringify(compressedValue).length;
        if (valueSize > CACHE_CONFIG.maxValueSize) {
          throw new HTTPException(400, { message: 'Cache value too large' });
        }

        await this.env.CACHE.put(namespacedKey, JSON.stringify(compressedValue), {
          expirationTtl: ttl
        });
      }

      this.metrics.sets++;
      return true;
    } catch (error) {
      this.metrics.errors++;
      console.error('Cache set error:', error);
      return false;
    }
  }

  /**
   * Delete value from cache
   * @param {string} key - Cache key
   * @param {Object} options - Cache options
   * @returns {boolean} Success
   */
  async delete(key, options = {}) {
    const namespacedKey = this.getNamespacedKey(key, options.prefix);

    try {
      // Remove from local cache
      this.localCache.delete(namespacedKey);

      // Remove from KV store
      if (this.env.CACHE) {
        await this.env.CACHE.delete(namespacedKey);
      }

      this.metrics.deletes++;
      return true;
    } catch (error) {
      this.metrics.errors++;
      console.error('Cache delete error:', error);
      return false;
    }
  }

  /**
   * Clear all cache entries with namespace
   * @returns {boolean} Success
   */
  async clear() {
    try {
      // Clear local cache
      this.localCache.clear();

      // Clear KV store entries with namespace
      if (this.env.CACHE) {
        const keys = await this.env.CACHE.list({ prefix: `${CACHE_CONFIG.namespace}:` });
        
        for (const key of keys.keys) {
          await this.env.CACHE.delete(key.name);
        }
      }

      return true;
    } catch (error) {
      this.metrics.errors++;
      console.error('Cache clear error:', error);
      return false;
    }
  }

  /**
   * Check if key exists in cache
   * @param {string} key - Cache key
   * @param {Object} options - Cache options
   * @returns {boolean} Key exists
   */
  async exists(key, options = {}) {
    const value = await this.get(key, options);
    return value !== null;
  }

  /**
   * Get cache statistics
   * @returns {Object} Cache statistics
   */
  getStats() {
    const hitRate = this.metrics.totalRequests > 0 
      ? (this.metrics.hits / this.metrics.totalRequests) * 100 
      : 0;

    return {
      ...this.metrics,
      hitRate: hitRate.toFixed(2) + '%',
      localCacheSize: this.localCache.size,
      config: CACHE_CONFIG
    };
  }

  /**
   * Reset cache statistics
   */
  resetStats() {
    this.metrics = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      errors: 0,
      totalRequests: 0
    };
  }

  /**
   * Clean expired entries from local cache
   */
  cleanup() {
    const now = Date.now();
    let cleaned = 0;

    for (const [key, entry] of this.localCache.entries()) {
      if (entry.expires <= now) {
        this.localCache.delete(key);
        cleaned++;
      }
    }

    return cleaned;
  }

  /**
   * Get multiple values from cache
   * @param {Array} keys - Array of cache keys
   * @param {Object} options - Cache options
   * @returns {Object} Key-value pairs
   */
  async getMultiple(keys, options = {}) {
    const results = {};
    
    for (const key of keys) {
      results[key] = await this.get(key, options);
    }

    return results;
  }

  /**
   * Set multiple values in cache
   * @param {Object} keyValuePairs - Object with key-value pairs
   * @param {Object} options - Cache options
   * @returns {boolean} Success
   */
  async setMultiple(keyValuePairs, options = {}) {
    const promises = Object.entries(keyValuePairs).map(([key, value]) => 
      this.set(key, value, options)
    );

    const results = await Promise.all(promises);
    return results.every(result => result === true);
  }

  /**
   * Increment numeric value in cache
   * @param {string} key - Cache key
   * @param {number} amount - Amount to increment
   * @param {Object} options - Cache options
   * @returns {number} New value
   */
  async increment(key, amount = 1, options = {}) {
    const currentValue = await this.get(key, options) || 0;
    const newValue = Number(currentValue) + amount;
    
    await this.set(key, newValue, options);
    return newValue;
  }

  /**
   * Decrement numeric value in cache
   * @param {string} key - Cache key
   * @param {number} amount - Amount to decrement
   * @param {Object} options - Cache options
   * @returns {number} New value
   */
  async decrement(key, amount = 1, options = {}) {
    return await this.increment(key, -amount, options);
  }

  /**
   * Health check
   * @returns {Object} Health status
   */
  async healthCheck() {
    try {
      const testKey = `health:${crypto.randomUUID()}`;
      const testValue = { timestamp: Date.now() };
      
      await this.set(testKey, testValue, { ttl: 60 });
      const retrievedValue = await this.get(testKey);
      await this.delete(testKey);
      
      const isHealthy = retrievedValue && retrievedValue.timestamp === testValue.timestamp;
      
      return {
        status: isHealthy ? 'healthy' : 'unhealthy',
        localCacheSize: this.localCache.size,
        stats: this.getStats(),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

/**
 * Cache Service Factory
 * @param {Object} env - Environment variables
 * @returns {CacheService} Cache service instance
 */
export function createCacheService(env) {
  return new CacheService(env);
}

/**
 * Cache middleware for Hono
 * @param {Object} options - Middleware options
 * @returns {Function} Middleware function
 */
export function cacheMiddleware(options = {}) {
  const { ttl = CACHE_CONFIG.defaultTTL, prefix = '', 
          skipMethods = ['POST', 'PUT', 'DELETE', 'PATCH'] } = options;

  return async (c, next) => {
    // Skip non-cacheable methods
    if (skipMethods.includes(c.req.method)) {
      return await next();
    }

    const cacheService = new CacheService(c.env);
    const cacheKey = `${c.req.method}:${c.req.url}`;
    
    try {
      // Try to get from cache
      const cachedResponse = await cacheService.get(cacheKey, { prefix, ttl });
      
      if (cachedResponse) {
        return c.json(cachedResponse);
      }

      // Execute request
      await next();

      // Cache successful responses
      if (c.res.status === 200 && c.res.headers.get('content-type')?.includes('application/json')) {
        const responseData = await c.res.json();
        await cacheService.set(cacheKey, responseData, { prefix, ttl });
        
        // Return cached response
        return c.json(responseData);
      }
    } catch (error) {
      console.error('Cache middleware error:', error);
      return await next();
    }
  };
}

export default {
  CacheService,
  createCacheService,
  cacheMiddleware,
  CACHE_CONFIG
};