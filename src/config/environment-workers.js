/**
 * Cloudflare Workers Environment Variables Management
 * Comprehensive configuration system for Cloudflare Workers deployment
 */

/**
 * Environment Configuration Schema
 * Defines all environment variables with validation rules and defaults
 */
const ENV_CONFIG = {
    // Application Configuration
    NODE_ENV: {
        required: true,
        default: 'development',
        validate: (value) => ['development', 'production', 'staging', 'test'].includes(value),
        description: 'Application environment mode'
    },
    APP_NAME: {
        required: true,
        default: 'MaiMaiNotePad',
        validate: (value) => value.length > 0 && value.length <= 50,
        description: 'Application name'
    },
    APP_VERSION: {
        required: true,
        default: '2.0.0',
        validate: (value) => /^\d+\.\d+\.\d+/.test(value),
        description: 'Application version'
    },
    APP_URL: {
        required: true,
        validate: (value) => /^https?:\/\/.+/.test(value),
        description: 'Application URL'
    },

    // Cloudflare Configuration
    CLOUDFLARE_ACCOUNT_ID: {
        required: true,
        validate: (value) => /^[a-f0-9]{32}$/.test(value),
        description: 'Cloudflare Account ID'
    },
    CLOUDFLARE_ZONE_ID: {
        required: true,
        validate: (value) => /^[a-f0-9]{32}$/.test(value),
        description: 'Cloudflare Zone ID'
    },

    // D1 Database Configuration
    D1_DATABASE_ID: {
        required: true,
        validate: (value) => value.length > 0,
        description: 'D1 Database ID'
    },
    D1_DATABASE_NAME: {
        required: true,
        default: 'maimainotepad_db',
        validate: (value) => /^[a-zA-Z0-9_]+$/.test(value),
        description: 'D1 Database name'
    },

    // R2 Storage Configuration
    R2_BUCKET_NAME: {
        required: true,
        default: 'maimainotepad-storage',
        validate: (value) => /^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(value) && value.length >= 3 && value.length <= 63,
        description: 'R2 Bucket name'
    },
    R2_BUCKET_URL: {
        required: true,
        validate: (value) => /^https?:\/\/.+/.test(value),
        description: 'R2 Bucket URL'
    },
    R2_ACCESS_KEY_ID: {
        required: true,
        validate: (value) => value.length >= 20,
        description: 'R2 Access Key ID'
    },
    R2_SECRET_ACCESS_KEY: {
        required: true,
        validate: (value) => value.length >= 40,
        description: 'R2 Secret Access Key'
    },

    // JWT Configuration
    JWT_SECRET: {
        required: true,
        validate: (value) => value.length >= 32,
        description: 'JWT Secret Key (minimum 32 characters)'
    },
    JWT_REFRESH_SECRET: {
        required: true,
        validate: (value) => value.length >= 32,
        description: 'JWT Refresh Secret Key (minimum 32 characters)'
    },
    JWT_EXPIRES_IN: {
        required: true,
        default: '15m',
        validate: (value) => /^\d+[smhd]$/.test(value),
        description: 'JWT Expiration Time'
    },
    JWT_REFRESH_EXPIRES_IN: {
        required: true,
        default: '7d',
        validate: (value) => /^\d+[smhd]$/.test(value),
        description: 'JWT Refresh Token Expiration Time'
    },

    // Security Configuration
    BCRYPT_ROUNDS: {
        required: true,
        default: 12,
        validate: (value) => Number(value) >= 10 && Number(value) <= 20,
        description: 'Bcrypt Hash Rounds'
    },
    RATE_LIMIT_WINDOW_MS: {
        required: true,
        default: 900000, // 15 minutes
        validate: (value) => Number(value) > 0,
        description: 'Rate Limit Window (milliseconds)'
    },
    RATE_LIMIT_MAX_REQUESTS: {
        required: true,
        default: 100,
        validate: (value) => Number(value) > 0,
        description: 'Rate Limit Max Requests'
    },
    CORS_ORIGIN: {
        required: true,
        validate: (value) => /^https?:\/\/.+/.test(value),
        description: 'CORS Origin URL'
    },

    // Email Configuration (Optional)
    SMTP_HOST: {
        required: false,
        default: 'smtp.gmail.com',
        validate: (value) => value.length > 0,
        description: 'SMTP Host'
    },
    SMTP_PORT: {
        required: false,
        default: 587,
        validate: (value) => Number(value) > 0 && Number(value) <= 65535,
        description: 'SMTP Port'
    },
    SMTP_USER: {
        required: false,
        validate: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        description: 'SMTP Username (email)'
    },
    SMTP_PASS: {
        required: false,
        validate: (value) => value.length > 0,
        description: 'SMTP Password'
    },
    SMTP_FROM: {
        required: false,
        validate: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        description: 'SMTP From Email'
    },

    // Analytics Configuration
    ANALYTICS_ENABLED: {
        required: true,
        default: true,
        validate: (value) => ['true', 'false'].includes(String(value).toLowerCase()),
        description: 'Analytics Enabled'
    },
    ANALYTICS_RETENTION_DAYS: {
        required: true,
        default: 30,
        validate: (value) => Number(value) > 0 && Number(value) <= 365,
        description: 'Analytics Data Retention (days)'
    },

    // Session Configuration
    SESSION_TIMEOUT_MINUTES: {
        required: true,
        default: 30,
        validate: (value) => Number(value) > 0,
        description: 'Session Timeout (minutes)'
    },
    SESSION_CLEANUP_INTERVAL_HOURS: {
        required: true,
        default: 24,
        validate: (value) => Number(value) > 0,
        description: 'Session Cleanup Interval (hours)'
    },

    // Backup Configuration
    BACKUP_ENABLED: {
        required: true,
        default: true,
        validate: (value) => ['true', 'false'].includes(String(value).toLowerCase()),
        description: 'Backup Enabled'
    },
    BACKUP_INTERVAL_HOURS: {
        required: true,
        default: 24,
        validate: (value) => Number(value) > 0,
        description: 'Backup Interval (hours)'
    },
    BACKUP_RETENTION_DAYS: {
        required: true,
        default: 7,
        validate: (value) => Number(value) > 0,
        description: 'Backup Retention (days)'
    },

    // Performance Configuration
    CACHE_TTL_SECONDS: {
        required: true,
        default: 3600,
        validate: (value) => Number(value) > 0,
        description: 'Cache TTL (seconds)'
    },
    MAX_UPLOAD_SIZE_MB: {
        required: true,
        default: 10,
        validate: (value) => Number(value) > 0 && Number(value) <= 100,
        description: 'Maximum Upload Size (MB)'
    },
    COMPRESSION_ENABLED: {
        required: true,
        default: true,
        validate: (value) => ['true', 'false'].includes(String(value).toLowerCase()),
        description: 'Compression Enabled'
    },

    // Development Configuration
    DEBUG_MODE: {
        required: false,
        default: false,
        validate: (value) => ['true', 'false'].includes(String(value).toLowerCase()),
        description: 'Debug Mode'
    },
    LOG_LEVEL: {
        required: true,
        default: 'info',
        validate: (value) => ['error', 'warn', 'info', 'debug'].includes(value),
        description: 'Log Level'
    },
    ENABLE_SWAGGER: {
        required: false,
        default: true,
        validate: (value) => ['true', 'false'].includes(String(value).toLowerCase()),
        description: 'Enable Swagger Documentation'
    },

    // Security Keys
    API_KEY_SECRET: {
        required: true,
        validate: (value) => value.length >= 32,
        description: 'API Key Secret (minimum 32 characters)'
    },
    CSRF_SECRET: {
        required: true,
        validate: (value) => value.length >= 32,
        description: 'CSRF Secret (minimum 32 characters)'
    },
    ENCRYPTION_KEY: {
        required: true,
        validate: (value) => value.length === 32,
        description: 'Encryption Key (exactly 32 characters)'
    },

    // External Services (Optional)
    WEBHOOK_SECRET: {
        required: false,
        validate: (value) => value.length >= 16,
        description: 'Webhook Secret (minimum 16 characters)'
    },
    SLACK_WEBHOOK_URL: {
        required: false,
        validate: (value) => /^https:\/\/hooks\.slack\.com\/services\/.+/.test(value),
        description: 'Slack Webhook URL'
    },
    DISCORD_WEBHOOK_URL: {
        required: false,
        validate: (value) => /^https:\/\/discord\.com\/api\/webhooks\/.+/.test(value),
        description: 'Discord Webhook URL'
    }
};

/**
 * Environment Validator Class
 * Validates environment variables against defined schema
 */
class EnvironmentValidator {
    constructor(config = ENV_CONFIG) {
        this.config = config;
        this.errors = [];
        this.warnings = [];
    }

    /**
     * Validate all environment variables
     * @returns {Object} Validation result
     */
    validateAll() {
        this.errors = [];
        this.warnings = [];

        for (const [key, schema] of Object.entries(this.config)) {
            this.validateVariable(key, schema);
        }

        return {
            valid: this.errors.length === 0,
            errors: this.errors,
            warnings: this.warnings,
            summary: this.generateSummary()
        };
    }

    /**
     * Validate a single environment variable
     * @param {string} key - Environment variable name
     * @param {Object} schema - Validation schema
     */
    validateVariable(key, schema) {
        const value = process.env[key];

        // Check if required
        if (schema.required && !value) {
            this.errors.push({
                key,
                message: `Required environment variable ${key} is missing`,
                type: 'missing'
            });
            return;
        }

        // Skip validation if optional and not provided
        if (!schema.required && !value) {
            if (schema.default) {
                this.warnings.push({
                    key,
                    message: `Optional environment variable ${key} not set, using default: ${schema.default}`,
                    type: 'default'
                });
            }
            return;
        }

        // Validate value
        if (schema.validate && !schema.validate(value)) {
            this.errors.push({
                key,
                message: `Invalid value for ${key}: ${value}. ${schema.description}`,
                type: 'invalid'
            });
            return;
        }

        // Check for weak values in production
        if (process.env.NODE_ENV === 'production' && this.isWeakValue(key, value)) {
            this.warnings.push({
                key,
                message: `Weak value detected for ${key} in production environment`,
                type: 'security'
            });
        }
    }

    /**
     * Check if a value is considered weak for security purposes
     * @param {string} key - Environment variable name
     * @param {string} value - Value to check
     * @returns {boolean}
     */
    isWeakValue(key, value) {
        const weakPatterns = [
            /^password$/i,
            /^123/,
            /^admin$/i,
            /^test$/i,
            /^default$/i,
            /^secret$/i
        ];

        return weakPatterns.some(pattern => pattern.test(value));
    }

    /**
     * Generate validation summary
     * @returns {Object}
     */
    generateSummary() {
        const total = Object.keys(this.config).length;
        const missing = this.errors.filter(e => e.type === 'missing').length;
        const invalid = this.errors.filter(e => e.type === 'invalid').length;
        const securityWarnings = this.warnings.filter(w => w.type === 'security').length;

        return {
            total,
            missing,
            invalid,
            warnings: this.warnings.length,
            securityWarnings,
            status: this.errors.length === 0 ? 'VALID' : 'INVALID'
        };
    }
}

/**
 * Environment Manager Class
 * Manages environment variables with validation and defaults
 */
class EnvironmentManager {
    constructor(validator = new EnvironmentValidator()) {
        this.validator = validator;
        this.cache = new Map();
    }

    /**
     * Initialize environment
     * @returns {Object} Initialization result
     */
    initialize() {
        const validation = this.validator.validateAll();

        if (!validation.valid) {
            throw new Error(`Environment validation failed:\n${validation.errors.map(e => `- ${e.message}`).join('\n')}`);
        }

        // Set defaults for missing optional variables
        this.setDefaults();

        return {
            success: true,
            warnings: validation.warnings,
            summary: validation.summary
        };
    }

    /**
     * Set default values for optional environment variables
     */
    setDefaults() {
        for (const [key, schema] of Object.entries(ENV_CONFIG)) {
            if (!schema.required && !process.env[key] && schema.default !== undefined) {
                process.env[key] = String(schema.default);
            }
        }
    }

    /**
     * Get environment variable with type conversion
     * @param {string} key - Environment variable name
     * @param {*} defaultValue - Default value if not found
     * @returns {*}
     */
    get(key, defaultValue = null) {
        if (this.cache.has(key)) {
            return this.cache.get(key);
        }

        const value = process.env[key];
        if (value === undefined) {
            return defaultValue;
        }

        // Type conversion
        const convertedValue = this.convertValue(value);
        this.cache.set(key, convertedValue);
        return convertedValue;
    }

    /**
     * Convert string value to appropriate type
     * @param {string} value - String value to convert
     * @returns {*}
     */
    convertValue(value) {
        // Boolean conversion
        if (value.toLowerCase() === 'true') return true;
        if (value.toLowerCase() === 'false') return false;

        // Number conversion
        if (/^\d+$/.test(value)) return Number(value);

        // JSON conversion
        try {
            return JSON.parse(value);
        } catch {
            // Return as string if not JSON
        }

        return value;
    }

    /**
     * Get all environment variables as object
     * @returns {Object}
     */
    getAll() {
        const result = {};
        for (const key of Object.keys(ENV_CONFIG)) {
            result[key] = this.get(key);
        }
        return result;
    }

    /**
     * Check if environment is production
     * @returns {boolean}
     */
    isProduction() {
        return this.get('NODE_ENV') === 'production';
    }

    /**
     * Check if environment is development
     * @returns {boolean}
     */
    isDevelopment() {
        return this.get('NODE_ENV') === 'development';
    }

    /**
     * Clear cache
     */
    clearCache() {
        this.cache.clear();
    }
}

/**
 * Workers Environment Processor
 * Processes environment variables for Cloudflare Workers
 */
class WorkersEnvProcessor {
    constructor(env = {}) {
        this.env = env;
        this.processed = new Map();
    }

    /**
     * Process environment bindings from Workers
     * @param {Object} env - Workers environment bindings
     * @returns {Object} Processed environment
     */
    process(env = this.env) {
        const processed = {};

        // Process D1 database binding
        if (env.DB) {
            processed.DATABASE = env.DB;
        }

        // Process R2 storage binding
        if (env.STORAGE) {
            processed.STORAGE = env.STORAGE;
        }

        // Process KV namespace binding
        if (env.KV) {
            processed.KV = env.KV;
        }

        // Process environment variables
        for (const [key, value] of Object.entries(env)) {
            if (typeof value === 'string') {
                processed[key] = this.processValue(value);
            } else {
                processed[key] = value;
            }
        }

        return processed;
    }

    /**
     * Process individual value
     * @param {string} value - Value to process
     * @returns {*}
     */
    processValue(value) {
        // Boolean conversion
        if (value.toLowerCase() === 'true') return true;
        if (value.toLowerCase() === 'false') return false;

        // Number conversion
        if (/^\d+$/.test(value)) return Number(value);

        // Return as string
        return value;
    }

    /**
     * Validate Workers environment
     * @param {Object} env - Workers environment
     * @returns {Object} Validation result
     */
    validate(env = this.env) {
        const errors = [];
        const warnings = [];

        // Check required bindings
        if (!env.DB) {
            errors.push('D1 database binding (DB) is required');
        }

        if (!env.STORAGE) {
            warnings.push('R2 storage binding (STORAGE) is not configured');
        }

        if (!env.KV) {
            warnings.push('KV namespace binding (KV) is not configured');
        }

        // Validate JWT secrets
        if (!env.JWT_SECRET || env.JWT_SECRET.length < 32) {
            errors.push('JWT_SECRET must be at least 32 characters');
        }

        if (!env.JWT_REFRESH_SECRET || env.JWT_REFRESH_SECRET.length < 32) {
            errors.push('JWT_REFRESH_SECRET must be at least 32 characters');
        }

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    }
}

/**
 * Utility Functions
 */

/**
 * Generate secure random string
 * @param {number} length - Length of string to generate
 * @returns {string}
 */
function generateSecureString(length = 32) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

/**
 * Mask sensitive value
 * @param {string} value - Value to mask
 * @returns {string}
 */
function maskValue(value) {
    if (!value || value.length < 8) {
        return '***';
    }
    return value.substring(0, 4) + '***' + value.substring(value.length - 4);
}

/**
 * Get environment info for debugging
 * @param {EnvironmentManager} manager - Environment manager instance
 * @returns {Object}
 */
function getEnvironmentInfo(manager) {
    const allEnv = manager.getAll();
    const masked = {};

    for (const [key, value] of Object.entries(allEnv)) {
        if (key.includes('SECRET') || key.includes('PASSWORD') || key.includes('KEY')) {
            masked[key] = maskValue(String(value));
        } else {
            masked[key] = value;
        }
    }

    return {
        environment: manager.get('NODE_ENV'),
        isProduction: manager.isProduction(),
        isDevelopment: manager.isDevelopment(),
        variables: masked,
        timestamp: new Date().toISOString()
    };
}

// Export all components
export {
    ENV_CONFIG,
    EnvironmentValidator,
    EnvironmentManager,
    WorkersEnvProcessor,
    generateSecureString,
    maskValue,
    getEnvironmentInfo
};

// Default export for convenience
export default {
    ENV_CONFIG,
    EnvironmentValidator,
    EnvironmentManager,
    WorkersEnvProcessor,
    generateSecureString,
    maskValue,
    getEnvironmentInfo
};