#!/usr/bin/env node

const { program } = require('commander');
const { scanFiles } = require('./scanner');
const { generateReport } = require('./reporter');
const chalk = require('chalk');
const path = require('path');

program
  .name('skillguard')
  .description('Security scanner for OpenClaw skill files')
  .version('1.0.0');

program
  .command('scan <path>')
  .description('Scan skill files for security vulnerabilities')
  .option('-o, --output <format>', 'Output format (text|json)', 'text')
  .option('-s, --severity <level>', 'Minimum severity to report (low|medium|high|critical)', 'low')
  .option('--no-color', 'Disable colored output')
  .action(async (targetPath, options) => {
    console.log(chalk.cyan.bold('\n🛡️  SkillGuard Security Scanner\n'));
    console.log(chalk.gray(`Scanning: ${path.resolve(targetPath)}\n`));
    
    try {
      const results = await scanFiles(targetPath);
      generateReport(results, options);
    } catch (err) {
      console.error(chalk.red(`Error: ${err.message}`));
      process.exit(1);
    }
  });

program
  .command('check <file>')
  .description('Check a single skill file')
  .action(async (file) => {
    console.log(chalk.cyan.bold('\n🛡️  SkillGuard - Single File Check\n'));
    
    try {
      const results = await scanFiles(file);
      generateReport(results, { output: 'text', severity: 'low' });
    } catch (err) {
      console.error(chalk.red(`Error: ${err.message}`));
      process.exit(1);
    }
  });

program.parse();
