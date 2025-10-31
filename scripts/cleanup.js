#!/usr/bin/env node

/**
 * 项目清理脚本
 * 用于清理项目中的冗余文件、临时文件和调试信息
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class ProjectCleaner {
  constructor() {
    this.stats = {
      filesDeleted: 0,
      filesModified: 0,
      spaceSaved: 0,
      errors: []
    };
    
    this.tempFilePatterns = [
      /\.log$/,
      /\.tmp$/,
      /\.temp$/,
      /\.bak$/,
      /\.backup$/,
      /\.old$/,
      /\.swp$/,
      /\.swo$/,
      /~$/,
      /\.DS_Store$/,
      /Thumbs\.db$/,
      /\.pid$/,
      /\.seed$/,
      /\.debug$/
    ];
    
    this.consolePatterns = [
      /console\.log\(/g,
      /console\.debug\(/g,
      /console\.warn\(/g,
      /console\.error\(/g
    ];
  }

  async confirmAction(message) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise((resolve) => {
      rl.question(`${message} (y/N): `, (answer) => {
        rl.close();
        resolve(answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes');
      });
    });
  }

  async findFiles(dir, pattern) {
    const files = [];
    
    try {
      const items = fs.readdirSync(dir);
      
      for (const item of items) {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory()) {
          // 跳过 node_modules 和 .git 目录
          if (item === 'node_modules' || item === '.git' || item === '.wrangler') {
            continue;
          }
          files.push(...await this.findFiles(fullPath, pattern));
        } else if (pattern.test(item)) {
          files.push(fullPath);
        }
      }
    } catch (error) {
      this.stats.errors.push(`无法读取目录 ${dir}: ${error.message}`);
    }
    
    return files;
  }

  async cleanTempFiles() {
    console.log('🔍 正在查找临时文件...');
    
    for (const pattern of this.tempFilePatterns) {
      const files = await this.findFiles(process.cwd(), pattern);
      
      for (const file of files) {
        try {
          const stats = fs.statSync(file);
          this.stats.spaceSaved += stats.size;
          fs.unlinkSync(file);
          this.stats.filesDeleted++;
          console.log(`🗑️  删除: ${path.relative(process.cwd(), file)}`);
        } catch (error) {
          this.stats.errors.push(`无法删除文件 ${file}: ${error.message}`);
        }
      }
    }
  }

  async cleanConsoleLogs() {
    console.log('\n🔍 正在查找调试日志...');
    
    const jsFiles = await this.findFiles(path.join(process.cwd(), 'src'), /\.js$/);
    
    for (const file of jsFiles) {
      try {
        let content = fs.readFileSync(file, 'utf8');
        let modified = false;
        
        // 检查是否包含 console 语句
        for (const pattern of this.consolePatterns) {
          if (pattern.test(content)) {
            // 替换 console 语句为注释
            content = content.replace(pattern, (match) => {
              // 保留错误日志，只注释调试日志
              if (match.includes('console.error') && file.includes('error-handler')) {
                return match; // 保留错误处理中的 console.error
              }
              return `// CLEANUP: ${match}`;
            });
            modified = true;
          }
        }
        
        if (modified) {
          fs.writeFileSync(file, content);
          this.stats.filesModified++;
          console.log(`📝 清理: ${path.relative(process.cwd(), file)}`);
        }
      } catch (error) {
        this.stats.errors.push(`无法处理文件 ${file}: ${error.message}`);
      }
    }
  }

  async cleanEmptyDirectories() {
    console.log('\n🔍 正在查找空目录...');
    
    const cleanEmptyDirs = async (dir) => {
      try {
        const items = fs.readdirSync(dir);
        let isEmpty = true;
        
        for (const item of items) {
          const fullPath = path.join(dir, item);
          const stat = fs.statSync(fullPath);
          
          if (stat.isDirectory()) {
            const subEmpty = await cleanEmptyDirs(fullPath);
            if (!subEmpty) {
              isEmpty = false;
            }
          } else {
            isEmpty = false;
          }
        }
        
        if (isEmpty && dir !== process.cwd()) {
          fs.rmdirSync(dir);
          console.log(`📂 删除空目录: ${path.relative(process.cwd(), dir)}`);
          return true;
        }
        
        return isEmpty;
      } catch (error) {
        return false;
      }
    };
    
    await cleanEmptyDirs(process.cwd());
  }

  async generateReport() {
    console.log('\n📊 清理报告');
    console.log('=' .repeat(50));
    console.log(`删除文件: ${this.stats.filesDeleted}`);
    console.log(`修改文件: ${this.stats.filesModified}`);
    console.log(`释放空间: ${(this.stats.spaceSaved / 1024).toFixed(2)} KB`);
    
    if (this.stats.errors.length > 0) {
      console.log(`\n⚠️  错误: ${this.stats.errors.length}`);
      this.stats.errors.forEach(error => console.log(`  - ${error}`));
    }
    
    console.log('\n✅ 清理完成！');
  }

  async run() {
    console.log('🚀 MaiMaiNotePad 项目清理工具');
    console.log('=' .repeat(50));
    
    try {
      // 清理临时文件
      if (await this.confirmAction('是否清理临时文件？')) {
        await this.cleanTempFiles();
      }
      
      // 清理调试日志
      if (await this.confirmAction('是否清理调试日志？')) {
        await this.cleanConsoleLogs();
      }
      
      // 清理空目录
      if (await this.confirmAction('是否清理空目录？')) {
        await this.cleanEmptyDirectories();
      }
      
      // 生成报告
      await this.generateReport();
      
    } catch (error) {
      console.error('清理过程出错:', error.message);
      process.exit(1);
    }
  }
}

// 如果直接运行此脚本
if (import.meta.url === `file://${process.argv[1]}`) {
  const cleaner = new ProjectCleaner();
  cleaner.run().catch(console.error);
}

export default ProjectCleaner;