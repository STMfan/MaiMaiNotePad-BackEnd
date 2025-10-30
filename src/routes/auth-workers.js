import { Hono } from 'hono';
import { sign, verify } from 'hono/jwt';
import { setCookie, getCookie, deleteCookie } from 'hono/cookie';
import { createHash } from 'crypto';
import { UserModel } from '../database/models/user-model.js';
import { authMiddleware, optionalAuthMiddleware } from '../middleware/auth-workers.js';
import { validateEmail, validatePassword } from '../utils/validators.js';

const auth = new Hono();

// Register new user
auth.post('/register', async (c) => {
  try {
    const { email, password, username, fullName } = await c.req.json();
    
    // Validation
    if (!email || !password || !username) {
      return c.json({ error: 'Email, password, and username are required' }, 400);
    }
    
    if (!validateEmail(email)) {
      return c.json({ error: 'Invalid email format' }, 400);
    }
    
    if (!validatePassword(password)) {
      return c.json({ 
        error: 'Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character' 
      }, 400);
    }
    
    const userModel = new UserModel(c.env.DB);
    
    // Check if user already exists
    const existingUser = await userModel.findByEmail(email);
    if (existingUser) {
      return c.json({ error: 'User already exists with this email' }, 409);
    }
    
    const existingUsername = await userModel.findByUsername(username);
    if (existingUsername) {
      return c.json({ error: 'Username already taken' }, 409);
    }
    
    // Create user
    const user = await userModel.create({
      email,
      username,
      fullName: fullName || username,
      password, // This will be hashed in the model
      role: 'user',
      isActive: true,
      createdAt: new Date().toISOString()
    });
    
    // Generate JWT token
    const payload = {
      userId: user.id,
      email: user.email,
      username: user.username,
      role: user.role,
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
    };
    
    const token = await sign(payload, c.env.JWT_SECRET);
    
    // Set HTTP-only cookie
    setCookie(c, 'auth_token', token, {
      httpOnly: true,
      secure: c.env.ENVIRONMENT === 'production',
      sameSite: 'Strict',
      maxAge: 24 * 60 * 60 * 1000, // 24 hours
      path: '/'
    });
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = user;
    
    return c.json({
      message: 'User registered successfully',
      user: userWithoutPassword,
      token
    }, 201);
    
  } catch (error) {
    console.error('Registration error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Login user
auth.post('/login', async (c) => {
  try {
    const { email, password } = await c.req.json();
    
    if (!email || !password) {
      return c.json({ error: 'Email and password are required' }, 400);
    }
    
    const userModel = new UserModel(c.env.DB);
    const user = await userModel.findByEmail(email);
    
    if (!user || !user.isActive) {
      return c.json({ error: 'Invalid credentials' }, 401);
    }
    
    // Verify password
    const isValidPassword = await userModel.verifyPassword(password, user.password);
    if (!isValidPassword) {
      return c.json({ error: 'Invalid credentials' }, 401);
    }
    
    // Update last login
    await userModel.updateLastLogin(user.id);
    
    // Generate JWT token
    const payload = {
      userId: user.id,
      email: user.email,
      username: user.username,
      role: user.role,
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
    };
    
    const token = await sign(payload, c.env.JWT_SECRET);
    
    // Set HTTP-only cookie
    setCookie(c, 'auth_token', token, {
      httpOnly: true,
      secure: c.env.ENVIRONMENT === 'production',
      sameSite: 'Strict',
      maxAge: 24 * 60 * 60 * 1000, // 24 hours
      path: '/'
    });
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = user;
    
    return c.json({
      message: 'Login successful',
      user: userWithoutPassword,
      token
    });
    
  } catch (error) {
    console.error('Login error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Logout user
auth.post('/logout', async (c) => {
  try {
    deleteCookie(c, 'auth_token');
    return c.json({ message: 'Logout successful' });
  } catch (error) {
    console.error('Logout error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get current user profile
auth.get('/profile', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const userModel = new UserModel(c.env.DB);
    
    const fullUser = await userModel.findById(user.userId);
    if (!fullUser) {
      return c.json({ error: 'User not found' }, 404);
    }
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = fullUser;
    
    return c.json({
      user: userWithoutPassword
    });
    
  } catch (error) {
    console.error('Profile error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Update user profile
auth.put('/profile', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const updates = await c.req.json();
    
    // Remove protected fields
    delete updates.id;
    delete updates.email;
    delete updates.password;
    delete updates.role;
    delete updates.createdAt;
    
    const userModel = new UserModel(c.env.DB);
    const updatedUser = await userModel.update(user.userId, {
      ...updates,
      updatedAt: new Date().toISOString()
    });
    
    if (!updatedUser) {
      return c.json({ error: 'User not found' }, 404);
    }
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = updatedUser;
    
    return c.json({
      message: 'Profile updated successfully',
      user: userWithoutPassword
    });
    
  } catch (error) {
    console.error('Profile update error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Change password
auth.put('/password', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const { currentPassword, newPassword } = await c.req.json();
    
    if (!currentPassword || !newPassword) {
      return c.json({ error: 'Current password and new password are required' }, 400);
    }
    
    if (!validatePassword(newPassword)) {
      return c.json({ 
        error: 'New password must be at least 8 characters long and contain uppercase, lowercase, number, and special character' 
      }, 400);
    }
    
    const userModel = new UserModel(c.env.DB);
    const currentUser = await userModel.findById(user.userId);
    
    if (!currentUser) {
      return c.json({ error: 'User not found' }, 404);
    }
    
    // Verify current password
    const isValidPassword = await userModel.verifyPassword(currentPassword, currentUser.password);
    if (!isValidPassword) {
      return c.json({ error: 'Current password is incorrect' }, 400);
    }
    
    // Update password
    await userModel.updatePassword(user.userId, newPassword);
    
    return c.json({ message: 'Password changed successfully' });
    
  } catch (error) {
    console.error('Password change error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Refresh token
auth.post('/refresh', optionalAuthMiddleware, async (c) => {
  try {
    const token = getCookie(c, 'auth_token');
    
    if (!token) {
      return c.json({ error: 'No token provided' }, 401);
    }
    
    let payload;
    try {
      payload = await verify(token, c.env.JWT_SECRET);
    } catch (error) {
      return c.json({ error: 'Invalid token' }, 401);
    }
    
    // Check if user still exists and is active
    const userModel = new UserModel(c.env.DB);
    const user = await userModel.findById(payload.userId);
    
    if (!user || !user.isActive) {
      return c.json({ error: 'User not found or inactive' }, 401);
    }
    
    // Generate new token
    const newPayload = {
      userId: user.id,
      email: user.email,
      username: user.username,
      role: user.role,
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
    };
    
    const newToken = await sign(newPayload, c.env.JWT_SECRET);
    
    // Set new cookie
    setCookie(c, 'auth_token', newToken, {
      httpOnly: true,
      secure: c.env.ENVIRONMENT === 'production',
      sameSite: 'Strict',
      maxAge: 24 * 60 * 60 * 1000, // 24 hours
      path: '/'
    });
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = user;
    
    return c.json({
      message: 'Token refreshed successfully',
      user: userWithoutPassword,
      token: newToken
    });
    
  } catch (error) {
    console.error('Token refresh error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Request password reset
auth.post('/reset-password', async (c) => {
  try {
    const { email } = await c.req.json();
    
    if (!email) {
      return c.json({ error: 'Email is required' }, 400);
    }
    
    if (!validateEmail(email)) {
      return c.json({ error: 'Invalid email format' }, 400);
    }
    
    const userModel = new UserModel(c.env.DB);
    const user = await userModel.findByEmail(email);
    
    if (!user || !user.isActive) {
      // Don't reveal whether user exists
      return c.json({ message: 'If an account exists, a password reset link has been sent' });
    }
    
    // Generate reset token (simplified - in production, use proper token generation)
    const resetToken = createHash('sha256').update(`${user.id}-${Date.now()}`).digest('hex');
    const resetExpiry = new Date(Date.now() + 60 * 60 * 1000).toISOString(); // 1 hour
    
    // Store reset token
    await userModel.update(user.id, {
      resetToken,
      resetTokenExpiry: resetExpiry
    });
    
    // In a real implementation, you would send an email here
    // For now, we'll just return the token (not recommended in production)
    return c.json({
      message: 'Password reset link sent',
      resetToken // Remove this in production - send via email instead
    });
    
  } catch (error) {
    console.error('Password reset error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Reset password with token
auth.put('/reset-password/:token', async (c) => {
  try {
    const { token } = c.req.param();
    const { newPassword } = await c.req.json();
    
    if (!token || !newPassword) {
      return c.json({ error: 'Token and new password are required' }, 400);
    }
    
    if (!validatePassword(newPassword)) {
      return c.json({ 
        error: 'Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character' 
      }, 400);
    }
    
    const userModel = new UserModel(c.env.DB);
    const user = await userModel.findByResetToken(token);
    
    if (!user || !user.resetTokenExpiry || new Date() > new Date(user.resetTokenExpiry)) {
      return c.json({ error: 'Invalid or expired reset token' }, 400);
    }
    
    // Update password and clear reset token
    await userModel.update(user.id, {
      password: newPassword,
      resetToken: null,
      resetTokenExpiry: null,
      updatedAt: new Date().toISOString()
    });
    
    return c.json({ message: 'Password reset successfully' });
    
  } catch (error) {
    console.error('Password reset confirmation error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

export default auth;