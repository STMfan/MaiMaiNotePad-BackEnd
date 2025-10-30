#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

console.log('🚀 Starting Cloudflare Workers build process...');

async function build() {
  try {
    // Create dist directory if it doesn't exist
    const distDir = join(projectRoot, 'dist');
    await fs.mkdir(distDir, { recursive: true });

    // Copy source files to dist
    const srcDir = join(projectRoot, 'src');
    const workersDir = join(srcDir, 'workers');
    const utilsDir = join(srcDir, 'utils');
    
    console.log('📁 Copying source files...');
    
    // Copy main worker file
    const mainWorker = join(workersDir, 'index.js');
    const distMainWorker = join(distDir, 'index.js');
    
    let workerContent = await fs.readFile(mainWorker, 'utf-8');
    
    // Simple minification - remove comments and extra whitespace
    workerContent = workerContent
      .replace(/\/\*[\s\S]*?\*\//g, '') // Remove block comments
      .replace(/\/\/.*$/gm, '') // Remove line comments
      .replace(/\s+/g, ' ') // Collapse whitespace
      .trim();
    
    await fs.writeFile(distMainWorker, workerContent);
    
    console.log('✅ Main worker file processed');
    
    // Copy utility files
    if (await fs.access(utilsDir).then(() => true).catch(() => false)) {
      const distUtilsDir = join(distDir, 'utils');
      await fs.mkdir(distUtilsDir, { recursive: true });
      
      const utilsFiles = await fs.readdir(utilsDir);
      
      for (const file of utilsFiles) {
        if (file.endsWith('.js')) {
          const srcFile = join(utilsDir, file);
          const distFile = join(distUtilsDir, file);
          
          let content = await fs.readFile(srcFile, 'utf-8');
          
          // Simple minification
          content = content
            .replace(/\/\*[\s\S]*?\*\//g, '')
            .replace(/\/\/.*$/gm, '')
            .replace(/\s+/g, ' ')
            .trim();
          
          await fs.writeFile(distFile, content);
          console.log(`✅ Processed ${file}`);
        }
      }
    }
    
    // Update wrangler.toml to point to dist directory
    const wranglerPath = join(projectRoot, 'wrangler.toml');
    let wranglerContent = await fs.readFile(wranglerPath, 'utf-8');
    
    wranglerContent = wranglerContent.replace(
      /main = "[^"]*"/,
      'main = "dist/index.js"'
    );
    
    await fs.writeFile(wranglerPath, wranglerContent);
    
    console.log('✅ Updated wrangler.toml');
    
    // Create build info
    const buildInfo = {
      timestamp: new Date().toISOString(),
      version: process.env.npm_package_version || '2.0.0',
      node: process.version,
      files: await getFileList(distDir),
      size: await getDirectorySize(distDir)
    };
    
    await fs.writeFile(
      join(distDir, 'build-info.json'),
      JSON.stringify(buildInfo, null, 2)
    );
    
    console.log('✅ Build completed successfully!');
    console.log(`📊 Build info:`);
    console.log(`   Files: ${buildInfo.files.length}`);
    console.log(`   Size: ${(buildInfo.size / 1024).toFixed(2)} KB`);
    console.log(`   Timestamp: ${buildInfo.timestamp}`);
    
  } catch (error) {
    console.error('❌ Build failed:', error.message);
    process.exit(1);
  }
}

async function getFileList(dir, basePath = '') {
  const files = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    const relativePath = join(basePath, entry.name);
    
    if (entry.isDirectory()) {
      files.push(...await getFileList(fullPath, relativePath));
    } else {
      files.push(relativePath);
    }
  }
  
  return files;
}

async function getDirectorySize(dir) {
  let size = 0;
  const entries = await fs.readdir(dir, { withFileTypes: true });
  
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    
    if (entry.isDirectory()) {
      size += await getDirectorySize(fullPath);
    } else {
      const stats = await fs.stat(fullPath);
      size += stats.size;
    }
  }
  
  return size;
}

// Run build if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  build();
}