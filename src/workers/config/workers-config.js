/**
 * Cloudflare Workers Configuration
 * Environment variables and configuration for Cloudflare Workers deployment
 */

/**
 * Environment variables schema
 * @typedef {Object} EnvironmentVariables
 * @property {string} ENVIRONMENT - Environment (development, staging, production)
 * @property {string} JWT_SECRET - JWT secret key
 * @property {string} DATABASE_URL - D1 database binding
 * @property {string} MAIMAI_KV - KV namespace binding
 * @property {string} MAIMAI_R2 - R2 storage binding
 * @property {string} API_BASE_URL - API base URL
 * @property {string} ALLOWED_ORIGINS - Comma-separated allowed origins
 * @property {string} RATE_LIMIT_WINDOW_MS - Rate limit window in milliseconds
 * @property {string} RATE_LIMIT_MAX_REQUESTS - Maximum requests per window
 * @property {string} MAX_FILE_SIZE - Maximum file size in bytes
 * @property {string} UPLOAD_TIMEOUT_MS - Upload timeout in milliseconds
 * @property {string} CLEANUP_INTERVAL_MS - Cleanup interval in milliseconds
 * @property {string} LOG_LEVEL - Log level (debug, info, warn, error)
 * @property {string} ENABLE_ANALYTICS - Enable analytics (true/false)
 * @property {string} ANALYTICS_ENDPOINT - Analytics endpoint URL
 * @property {string} WEBHOOK_SECRET - Webhook secret for validation
 * @property {string} MAINTENANCE_MODE - Maintenance mode (true/false)
 * @property {string} MAINTENANCE_MESSAGE - Maintenance mode message
 */

/**
 * Default configuration values
 */
const DEFAULT_CONFIG = {
  // Environment
  ENVIRONMENT: 'development',
  
  // Security
  JWT_SECRET: 'your-jwt-secret-key-change-in-production',
  JWT_EXPIRES_IN: '7d',
  JWT_ALGORITHM: 'HS256',
  
  // CORS
  ALLOWED_ORIGINS: ['https://maimnp.tech', 'https://app.maimnp.tech', 'http://localhost:3000'],
  
  // Rate limiting
  RATE_LIMIT_WINDOW_MS: 15 * 60 * 1000, // 15 minutes
  RATE_LIMIT_MAX_REQUESTS: 100,
  RATE_LIMIT_SKIP_SUCCESSFUL_REQUESTS: false,
  
  // File upload
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  UPLOAD_TIMEOUT_MS: 5 * 60 * 1000, // 5 minutes
  CHUNK_SIZE: 5 * 1024 * 1024, // 5MB
  MAX_CHUNKS: 10,
  
  // File types
  ALLOWED_FILE_TYPES: [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'text/markdown',
    'application/json', 'application/xml', 'text/xml',
    'application/zip', 'application/x-zip-compressed', 'application/x-rar-compressed'
  ],
  
  // Cleanup
  CLEANUP_INTERVAL_MS: 24 * 60 * 60 * 1000, // 24 hours
  FILE_EXPIRY_DAYS: 30,
  TEMP_FILE_EXPIRY_HOURS: 24,
  
  // Logging
  LOG_LEVEL: 'info',
  ENABLE_REQUEST_LOGGING: true,
  ENABLE_ERROR_LOGGING: true,
  
  // Analytics
  ENABLE_ANALYTICS: false,
  ANALYTICS_ENDPOINT: 'https://analytics.maimnp.tech',
  ANALYTICS_BATCH_SIZE: 100,
  ANALYTICS_FLUSH_INTERVAL_MS: 60 * 1000, // 1 minute
  
  // Webhooks
  WEBHOOK_SECRET: 'your-webhook-secret-change-in-production',
  WEBHOOK_TIMEOUT_MS: 10 * 1000, // 10 seconds
  
  // Maintenance
  MAINTENANCE_MODE: false,
  MAINTENANCE_MESSAGE: 'Service is under maintenance. Please try again later.',
  
  // Health check
  HEALTH_CHECK_INTERVAL_MS: 30 * 1000, // 30 seconds
  HEALTH_CHECK_TIMEOUT_MS: 5 * 1000, // 5 seconds
  
  // Database
  DATABASE_MAX_CONNECTIONS: 10,
  DATABASE_TIMEOUT_MS: 30 * 1000, // 30 seconds
  DATABASE_RETRY_ATTEMPTS: 3,
  DATABASE_RETRY_DELAY_MS: 1000,
  
  // Cache
  CACHE_TTL_SECONDS: 3600, // 1 hour
  CACHE_MAX_KEYS: 10000,
  
  // Security
  BCRYPT_ROUNDS: 12,
  SESSION_TIMEOUT_MS: 24 * 60 * 60 * 1000, // 24 hours
  PASSWORD_MIN_LENGTH: 8,
  PASSWORD_REQUIRE_UPPERCASE: true,
  PASSWORD_REQUIRE_LOWERCASE: true,
  PASSWORD_REQUIRE_NUMBERS: true,
  PASSWORD_REQUIRE_SPECIAL_CHARS: true,
  
  // API
  API_BASE_URL: 'https://api.maimnp.tech',
  API_VERSION: 'v1',
  API_TIMEOUT_MS: 30 * 1000, // 30 seconds
  
  // Email (if using email services)
  EMAIL_ENABLED: false,
  EMAIL_FROM: 'official@maimnp.tech',
  EMAIL_VERIFICATION_REQUIRED: false,
  
  // File storage
  R2_BUCKET_NAME: 'maimai-files',
  R2_PUBLIC_URL: 'https://files.maimnp.tech',
  R2_CACHE_CONTROL: 'public, max-age=31536000',
  
  // Error handling
  ERROR_DETAIL_LEVEL: 'minimal', // minimal, detailed, debug
  ERROR_INCLUDE_STACK: false,
  ERROR_NOTIFICATION_ENABLED: false,
  
  // Performance
  ENABLE_COMPRESSION: true,
  ENABLE_ETAG: true,
  ENABLE_CORS_PREFLIGHT_CACHE: true,
  
  // Monitoring
  ENABLE_METRICS: false,
  METRICS_ENDPOINT: '/metrics',
  METRICS_UPDATE_INTERVAL_MS: 60 * 1000, // 1 minute
  
  // Backup
  BACKUP_ENABLED: false,
  BACKUP_INTERVAL_MS: 24 * 60 * 60 * 1000, // 24 hours
  BACKUP_RETENTION_DAYS: 7
};

/**
 * Configuration manager class
 */
export class ConfigurationManager {
  constructor(env = {}) {
    this.env = env;
    this.config = this.loadConfiguration();
  }
  
  /**
   * Load configuration from environment variables
   * @returns {Object} Configuration object
   */
  loadConfiguration() {
    const config = { ...DEFAULT_CONFIG };
    
    // Override with environment variables
    Object.keys(config).forEach(key => {
      const envKey = key.toUpperCase();
      if (this.env[envKey] !== undefined) {
        const value = this.env[envKey];
        
        // Type conversion
        if (typeof config[key] === 'boolean') {
          config[key] = value === 'true' || value === true;
        } else if (typeof config[key] === 'number') {
          config[key] = parseInt(value) || config[key];
        } else if (Array.isArray(config[key])) {
          config[key] = value.split(',').map(v => v.trim());
        } else {
          config[key] = value;
        }
      }
    });
    
    return config;
  }
  
  /**
   * Get configuration value
   * @param {string} key - Configuration key
   * @param {*} defaultValue - Default value if key not found
   * @returns {*} Configuration value
   */
  get(key, defaultValue = null) {
    return this.config[key] !== undefined ? this.config[key] : defaultValue;
  }
  
  /**
   * Set configuration value
   * @param {string} key - Configuration key
   * @param {*} value - Configuration value
   */
  set(key, value) {
    this.config[key] = value;
  }
  
  /**
   * Get all configuration
   * @returns {Object} Complete configuration
   */
  getAll() {
    return { ...this.config };
  }
  
  /**
   * Validate configuration
   * @returns {Object} Validation result
   */
  validate() {
    const errors = [];
    const warnings = [];
    
    // Required fields
    const requiredFields = ['JWT_SECRET', 'ENVIRONMENT'];
    requiredFields.forEach(field => {
      if (!this.config[field] || this.config[field] === DEFAULT_CONFIG[field]) {
        errors.push(`Missing or default ${field}`);
      }
    });
    
    // Security validations
    if (this.config.JWT_SECRET === DEFAULT_CONFIG.JWT_SECRET) {
      warnings.push('Using default JWT secret - change in production');
    }
    
    if (this.config.WEBHOOK_SECRET === DEFAULT_CONFIG.WEBHOOK_SECRET) {
      warnings.push('Using default webhook secret - change in production');
    }
    
    // File size validations
    if (this.config.MAX_FILE_SIZE > 100 * 1024 * 1024) {
      warnings.push('Large file size limit (>100MB) may impact performance');
    }
    
    // Rate limit validations
    if (this.config.RATE_LIMIT_MAX_REQUESTS > 1000) {
      warnings.push('High rate limit may impact performance');
    }
    
    return {
      valid: errors.length === 0,
      errors,
      warnings
    };
  }
  
  /**
   * Get environment-specific configuration
   * @param {string} environment - Environment name
   * @returns {Object} Environment-specific configuration
   */
  getEnvironmentConfig(environment) {
    const configs = {
      development: {
        LOG_LEVEL: 'debug',
        ENABLE_REQUEST_LOGGING: true,
        ENABLE_ERROR_LOGGING: true,
        ERROR_DETAIL_LEVEL: 'detailed',
        ERROR_INCLUDE_STACK: true,
        RATE_LIMIT_MAX_REQUESTS: 1000,
        MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
        ENABLE_ANALYTICS: false
      },
      staging: {
        LOG_LEVEL: 'info',
        ENABLE_REQUEST_LOGGING: true,
        ENABLE_ERROR_LOGGING: true,
        ERROR_DETAIL_LEVEL: 'minimal',
        ERROR_INCLUDE_STACK: false,
        RATE_LIMIT_MAX_REQUESTS: 200,
        MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
        ENABLE_ANALYTICS: true
      },
      production: {
        LOG_LEVEL: 'warn',
        ENABLE_REQUEST_LOGGING: false,
        ENABLE_ERROR_LOGGING: true,
        ERROR_DETAIL_LEVEL: 'minimal',
        ERROR_INCLUDE_STACK: false,
        RATE_LIMIT_MAX_REQUESTS: 100,
        MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
        ENABLE_ANALYTICS: true,
        ENABLE_METRICS: true,
        ERROR_NOTIFICATION_ENABLED: true
      }
    };
    
    return configs[environment] || configs.development;
  }
  
  /**
   * Apply environment-specific configuration
   * @param {string} environment - Environment name
   */
  applyEnvironmentConfig(environment) {
    const envConfig = this.getEnvironmentConfig(environment);
    Object.assign(this.config, envConfig);
  }
}

/**
 * Create configuration manager
 * @param {Object} env - Environment variables
 * @returns {ConfigurationManager} Configuration manager instance
 */
export function createConfigurationManager(env) {
  return new ConfigurationManager(env);
}

/**
 * Validate environment variables
 * @param {Object} env - Environment variables
 * @returns {Object} Validation result
 */
export function validateEnvironmentVariables(env) {
  const requiredBindings = [
    'MAIMAI_DB', // D1 database
    'MAIMAI_KV', // KV namespace
    'MAIMAI_R2'  // R2 storage
  ];
  
  const missingBindings = requiredBindings.filter(binding => !env[binding]);
  
  const requiredSecrets = [
    'JWT_SECRET',
    'WEBHOOK_SECRET'
  ];
  
  const missingSecrets = requiredSecrets.filter(secret => !env[secret]);
  
  return {
    valid: missingBindings.length === 0 && missingSecrets.length === 0,
    missingBindings,
    missingSecrets,
    warnings: []
  };
}

/**
 * Get wrangler configuration template
 * @returns {string} Wrangler configuration template
 */
export function getWranglerConfigTemplate() {
  return `name = "maimai-note-backend"
main = "src/workers/index.js"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

# Environment variables
[vars]
ENVIRONMENT = "development"
API_BASE_URL = "https://api.maimnp.tech"
ALLOWED_ORIGINS = "https://maimnp.tech,https://app.maimnp.tech"
RATE_LIMIT_WINDOW_MS = "900000"
RATE_LIMIT_MAX_REQUESTS = "100"
MAX_FILE_SIZE = "52428800"
UPLOAD_TIMEOUT_MS = "300000"
CLEANUP_INTERVAL_MS = "86400000"
LOG_LEVEL = "info"
ENABLE_ANALYTICS = "false"
MAINTENANCE_MODE = "false"

# Secrets (set using wrangler secret put)
# JWT_SECRET = "your-jwt-secret-here"
# WEBHOOK_SECRET = "your-webhook-secret-here"
# ANALYTICS_ENDPOINT = "your-analytics-endpoint-here"

# D1 Database
[[d1_databases]]
binding = "MAIMAI_DB"
database_name = "maimai-note-db"
database_id = "your-database-id"

# KV Namespaces
[[kv_namespaces]]
binding = "MAIMAI_KV"
id = "your-kv-namespace-id"
preview_id = "your-preview-kv-namespace-id"

# R2 Storage
[[r2_buckets]]
binding = "MAIMAI_R2"
bucket_name = "maimai-files"

# Environment-specific configurations
[env.staging.vars]
ENVIRONMENT = "staging"
LOG_LEVEL = "info"
RATE_LIMIT_MAX_REQUESTS = "200"

[env.production.vars]
ENVIRONMENT = "production"
LOG_LEVEL = "warn"
RATE_LIMIT_MAX_REQUESTS = "100"
ENABLE_ANALYTICS = "true"

# Custom domains
[env.production.routes]
pattern = "api.maimnp.tech/*"
zone_name = "maimnp.tech"

# Scheduled triggers
[triggers]
crons = ["0 2 * * *", "0 3 * * 0", "0 4 1 * *"]

# Build configuration
[build]
command = "npm run build"
cwd = "."
watch_dir = "src"

# Minification
minify = true

# Node.js compatibility
node_compat = true`;
}

/**
 * Environment configuration template
 * @returns {Object} Environment configuration template
 */
export function getEnvironmentTemplate() {
  return {
    development: {
      ENVIRONMENT: 'development',
      LOG_LEVEL: 'debug',
      RATE_LIMIT_MAX_REQUESTS: 1000,
      MAX_FILE_SIZE: 100 * 1024 * 1024,
      ENABLE_REQUEST_LOGGING: true,
      ERROR_DETAIL_LEVEL: 'detailed'
    },
    staging: {
      ENVIRONMENT: 'staging',
      LOG_LEVEL: 'info',
      RATE_LIMIT_MAX_REQUESTS: 200,
      MAX_FILE_SIZE: 50 * 1024 * 1024,
      ENABLE_REQUEST_LOGGING: true,
      ERROR_DETAIL_LEVEL: 'minimal'
    },
    production: {
      ENVIRONMENT: 'production',
      LOG_LEVEL: 'warn',
      RATE_LIMIT_MAX_REQUESTS: 100,
      MAX_FILE_SIZE: 50 * 1024 * 1024,
      ENABLE_REQUEST_LOGGING: false,
      ERROR_DETAIL_LEVEL: 'minimal',
      ENABLE_ANALYTICS: true,
      ENABLE_METRICS: true
    }
  };
}

// Export classes and functions individually (already exported above)