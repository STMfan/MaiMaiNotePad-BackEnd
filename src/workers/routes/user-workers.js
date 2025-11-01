/**
 * User management routes for Cloudflare Workers
 */

export async function handleUserRoutes(context, ...params) {
  const { request, env, config, log } = context;
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  try {
    // Route to specific user handlers
    if (path.includes('/profile') && method === 'GET') {
      return await handleGetProfile(context);
    } else if (path.includes('/profile') && method === 'PUT') {
      return await handleUpdateProfile(context);
    } else if (path.includes('/password') && method === 'PUT') {
      return await handleChangePassword(context);
    } else if (path.includes('/settings') && method === 'GET') {
      return await handleGetSettings(context);
    } else if (path.includes('/settings') && method === 'PUT') {
      return await handleUpdateSettings(context);
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'User endpoint not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('User route error', { error: error.message, path, method });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'User service error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetProfile(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get user profile from KV
    if (env.KV) {
      const userData = await env.KV.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        return new Response(JSON.stringify({
          user: {
            id: user.id,
            username: user.username,
            email: user.email,
            created_at: user.created_at,
            email_verified: user.email_verified,
            role: user.role
          }
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    // Fallback response
    return new Response(JSON.stringify({
      user: {
        id: userId,
        username: 'demo-user',
        email: 'demo@example.com',
        created_at: new Date().toISOString(),
        email_verified: true,
        role: 'user'
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get profile error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get user profile'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleUpdateProfile(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { username, email } = body;
    
    if (!username && !email) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Username or email is required for update'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Update user profile in KV
    if (env.KV) {
      const userData = await env.KV.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        
        if (username) user.username = username;
        if (email) user.email = email;
        user.updated_at = new Date().toISOString();
        
        await env.KV.put(`user:${userId}`, JSON.stringify(user));
        
        return new Response(JSON.stringify({
          message: 'Profile updated successfully',
          user: {
            id: user.id,
            username: user.username,
            email: user.email,
            updated_at: user.updated_at
          }
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    // Fallback response
    return new Response(JSON.stringify({
      message: 'Profile updated successfully (simulated)',
      user: {
        id: userId,
        username: username || 'demo-user',
        email: email || 'demo@example.com',
        updated_at: new Date().toISOString()
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Update profile error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to update user profile'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleChangePassword(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { currentPassword, newPassword } = body;
    
    if (!currentPassword || !newPassword) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Current password and new password are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (newPassword.length < 6) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'New password must be at least 6 characters'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Update password in KV
    if (env.KV) {
      const userData = await env.KV.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        
        // Verify current password (simplified)
        const hashedCurrentPassword = await hashPassword(currentPassword);
        if (hashedCurrentPassword !== user.password) {
          return new Response(JSON.stringify({ 
            error: 'Bad Request',
            message: 'Current password is incorrect'
          }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Update password
        user.password = await hashPassword(newPassword);
        user.updated_at = new Date().toISOString();
        
        await env.KV.put(`user:${userId}`, JSON.stringify(user));
        
        return new Response(JSON.stringify({
          message: 'Password changed successfully'
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    // Fallback response
    return new Response(JSON.stringify({
      message: 'Password changed successfully (simulated)'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Change password error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to change password'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetSettings(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get user settings from KV
    if (env.KV) {
      const settingsData = await env.KV.get(`user:${userId}:settings`);
      if (settingsData) {
        const settings = JSON.parse(settingsData);
        return new Response(JSON.stringify({ settings }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    // Default settings
    const defaultSettings = {
      theme: 'light',
      language: 'en',
      notifications: {
        email: true,
        push: false
      },
      privacy: {
        profile_visible: true,
        show_email: false
      }
    };
    
    return new Response(JSON.stringify({ settings: defaultSettings }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get settings error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get user settings'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleUpdateSettings(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { settings } = body;
    
    if (!settings) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Settings object is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Update user settings in KV
    if (env.KV) {
      await env.KV.put(`user:${userId}:settings`, JSON.stringify(settings));
      
      return new Response(JSON.stringify({
        message: 'Settings updated successfully',
        settings
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Fallback response
    return new Response(JSON.stringify({
      message: 'Settings updated successfully (simulated)',
      settings
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Update settings error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to update user settings'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Helper functions
async function getUserIdFromToken(request, config) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  
  const token = authHeader.substring(7);
  // In a real app, validate the JWT token and extract user ID
  // For now, return a demo user ID
  return 'demo-user-id';
}

async function hashPassword(password) {
  // Simple hash simulation - in production use proper crypto
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
}