/**
 * Error Handler Middleware for Cloudflare Workers
 * Provides centralized error handling with different levels of detail
 */

/**
 * Standard error response structure
 */
class AppError extends Error {
  constructor(message, statusCode = 500, details = null) {
    super(message);
    this.statusCode = statusCode;
    this.details = details;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Error handler middleware
 * @param {Error} error - The error object
 * @param {Request} request - The request object
 * @param {Object} env - Environment variables
 * @returns {Response} Error response
 */
export function errorHandler(error, request, env) {
  // Default error values
  let statusCode = 500;
  let message = 'Internal Server Error';
  let details = null;
  let shouldLog = true;

  // Determine environment
  const isDevelopment = env.ENVIRONMENT === 'development';
  const isProduction = env.ENVIRONMENT === 'production';

  // Handle different error types
  if (error instanceof AppError) {
    statusCode = error.statusCode;
    message = error.message;
    details = error.details;
    shouldLog = error.isOperational;
  } else if (error.name === 'ValidationError') {
    statusCode = 400;
    message = 'Validation Error';
    details = error.message;
  } else if (error.name === 'UnauthorizedError') {
    statusCode = 401;
    message = 'Unauthorized';
  } else if (error.name === 'ForbiddenError') {
    statusCode = 403;
    message = 'Forbidden';
  } else if (error.name === 'NotFoundError') {
    statusCode = 404;
    message = 'Not Found';
  } else if (error.name === 'RateLimitError') {
    statusCode = 429;
    message = 'Too Many Requests';
    details = { retryAfter: error.retryAfter };
  } else if (error.message?.includes('timeout')) {
    statusCode = 504;
    message = 'Gateway Timeout';
  } else if (error.message?.includes('ECONNREFUSED')) {
    statusCode = 503;
    message = 'Service Unavailable';
  }

  // Log error if needed
  if (shouldLog) {
    const errorLog = {
      timestamp: new Date().toISOString(),
      statusCode,
      message: error.message,
      url: request.url,
      method: request.method,
      userAgent: request.headers.get('User-Agent'),
      ...(isDevelopment && { stack: error.stack })
    };

    // Log to console (in production, this would go to a logging service)
    console.error('Error:', JSON.stringify(errorLog, null, 2));
  }

  // Build response based on environment
  const responseBody = {
    error: {
      message,
      statusCode,
      timestamp: new Date().toISOString(),
      requestId: crypto.randomUUID()
    }
  };

  // Add details in development/staging
  if (!isProduction && details) {
    responseBody.error.details = details;
  }

  // Add stack trace in development only
  if (isDevelopment) {
    responseBody.error.stack = error.stack;
  }

  return new Response(JSON.stringify(responseBody), {
    status: statusCode,
    headers: {
      'Content-Type': 'application/json',
      'X-Error-Message': message
    }
  });
}

/**
 * Create a validation error
 * @param {string} message - Error message
 * @param {Object} details - Additional error details
 * @returns {AppError} Validation error
 */
export function createValidationError(message, details = null) {
  const error = new AppError(message, 400, details);
  error.name = 'ValidationError';
  return error;
}

/**
 * Create a not found error
 * @param {string} resource - Resource name
 * @returns {AppError} Not found error
 */
export function createNotFoundError(resource = 'Resource') {
  const error = new AppError(`${resource} not found`, 404);
  error.name = 'NotFoundError';
  return error;
}

/**
 * Create an unauthorized error
 * @param {string} message - Error message
 * @returns {AppError} Unauthorized error
 */
export function createUnauthorizedError(message = 'Unauthorized') {
  const error = new AppError(message, 401);
  error.name = 'UnauthorizedError';
  return error;
}

/**
 * Create a forbidden error
 * @param {string} message - Error message
 * @returns {AppError} Forbidden error
 */
export function createForbiddenError(message = 'Forbidden') {
  const error = new AppError(message, 403);
  error.name = 'ForbiddenError';
  return error;
}

/**
 * Create a rate limit error
 * @param {number} retryAfter - Retry after seconds
 * @returns {AppError} Rate limit error
 */
export function createRateLimitError(retryAfter = 60) {
  const error = new AppError('Too Many Requests', 429, { retryAfter });
  error.name = 'RateLimitError';
  return error;
}

/**
 * Wrap async function with error handling
 * @param {Function} fn - Async function to wrap
 * @returns {Function} Wrapped function with error handling
 */
export function asyncHandler(fn) {
  return async (request, env, ctx) => {
    try {
      return await fn(request, env, ctx);
    } catch (error) {
      return errorHandler(error, request, env);
    }
  };
}

export { AppError };