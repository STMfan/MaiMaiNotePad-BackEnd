/**
 * Authentication routes for Cloudflare Workers
 */

export async function handleAuthRoutes(context, ...params) {
  const { request, env, config, log } = context;
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  try {
    // Route to specific auth handlers
    if (path.includes('/register') && method === 'POST') {
      return await handleRegister(context);
    } else if (path.includes('/login') && method === 'POST') {
      return await handleLogin(context);
    } else if (path.includes('/logout') && method === 'POST') {
      return await handleLogout(context);
    } else if (path.includes('/refresh') && method === 'POST') {
      return await handleRefreshToken(context);
    } else if (path.includes('/forgot-password') && method === 'POST') {
      return await handleForgotPassword(context);
    } else if (path.includes('/reset-password') && method === 'POST') {
      return await handleResetPassword(context);
    } else if (path.includes('/verify-email') && method === 'POST') {
      return await handleVerifyEmail(context);
    } else if (path.includes('/me') && method === 'GET') {
      return await handleGetCurrentUser(context);
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Auth endpoint not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Auth route error', { error: error.message, path, method });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Authentication service error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleRegister(context) {
  const { request, env, config, log } = context;
  
  try {
    const body = await request.json();
    const { username, email, password } = body;
    
    if (!username || !email || !password) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Username, email, and password are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Simple validation
    if (password.length < 6) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Password must be at least 6 characters'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Generate user ID
    const userId = crypto.randomUUID();
    const hashedPassword = await hashPassword(password);
    const now = new Date().toISOString();
    
    // Store user in KV (simplified for demo)
    if (env.KV) {
      const userData = {
        id: userId,
        username,
        email,
        password: hashedPassword,
        created_at: now,
        updated_at: now,
        email_verified: false,
        role: 'user'
      };
      
      await env.KV.put(`user:${userId}`, JSON.stringify(userData));
      await env.KV.put(`user:email:${email}`, userId);
      
      // Generate JWT token
      const token = await generateJWT(userId, config);
      
      return new Response(JSON.stringify({
        message: 'User registered successfully',
        user: {
          id: userId,
          username,
          email,
          created_at: now
        },
        token
      }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Fallback response if KV not available
    return new Response(JSON.stringify({
      message: 'Registration endpoint available (KV not configured)',
      user: {
        id: userId,
        username,
        email
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Registration error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Registration failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleLogin(context) {
  const { request, env, config, log } = context;
  
  try {
    const body = await request.json();
    const { email, password } = body;
    
    if (!email || !password) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Email and password are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Simple login simulation
    if (env.KV) {
      const userId = await env.KV.get(`user:email:${email}`);
      if (userId) {
        const userData = await env.KV.get(`user:${userId}`);
        if (userData) {
          const user = JSON.parse(userData);
          
          // Verify password (simplified)
          if (await verifyPassword(password, user.password)) {
            const token = await generateJWT(userId, config);
            
            return new Response(JSON.stringify({
              message: 'Login successful',
              user: {
                id: userId,
                username: user.username,
                email: user.email
              },
              token
            }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' }
            });
          }
        }
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Unauthorized',
      message: 'Invalid email or password'
    }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Login error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Login failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleLogout(context) {
  const { request, env, config, log } = context;
  
  // Simple logout - in a real app, you might invalidate the token
  return new Response(JSON.stringify({ 
    message: 'Logout successful'
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

async function handleRefreshToken(context) {
  const { request, env, config, log } = context;
  
  try {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'No valid token provided'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const oldToken = authHeader.substring(7);
    // In a real app, validate the old token and extract user info
    
    const newToken = await generateJWT('user-id', config);
    
    return new Response(JSON.stringify({ 
      token: newToken
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Token refresh error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Token refresh failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleForgotPassword(context) {
  const { request, env, config, log } = context;
  
  try {
    const body = await request.json();
    const { email } = body;
    
    if (!email) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Email is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Simulate password reset email
    return new Response(JSON.stringify({ 
      message: 'Password reset email sent (simulated)'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Forgot password error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Password reset request failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleResetPassword(context) {
  const { request, env, config, log } = context;
  
  try {
    const body = await request.json();
    const { token, newPassword } = body;
    
    if (!token || !newPassword) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Token and new password are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Simulate password reset
    return new Response(JSON.stringify({ 
      message: 'Password reset successful (simulated)'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Reset password error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Password reset failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleVerifyEmail(context) {
  const { request, env, config, log } = context;
  
  try {
    const body = await request.json();
    const { token } = body;
    
    if (!token) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Verification token is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Simulate email verification
    return new Response(JSON.stringify({ 
      message: 'Email verified successfully (simulated)'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Email verification error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Email verification failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetCurrentUser(context) {
  const { request, env, config, log } = context;
  
  try {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'No valid token provided'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const token = authHeader.substring(7);
    // In a real app, validate token and get user info
    
    return new Response(JSON.stringify({ 
      user: {
        id: 'user-id',
        username: 'demo-user',
        email: 'demo@example.com'
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get current user error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get user information'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Helper functions
async function hashPassword(password) {
  // Simple hash simulation - in production use proper crypto
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function verifyPassword(password, hashedPassword) {
  const hashed = await hashPassword(password);
  return hashed === hashedPassword;
}

async function generateJWT(userId, config) {
  // Simple JWT simulation - in production use proper JWT library
  const header = { alg: 'HS256', typ: 'JWT' };
  const payload = {
    userId,
    exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24) // 24 hours
  };
  
  const secret = config.get('JWT_SECRET', 'default-secret');
  
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const signature = btoa(`${encodedHeader}.${encodedPayload}.${secret}`);
  
  return `${encodedHeader}.${encodedPayload}.${signature}`;
}