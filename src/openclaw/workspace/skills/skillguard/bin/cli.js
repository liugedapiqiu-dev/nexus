#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { scanFile, scanDirectory, formatReport } from '../lib/scanner.js';
import fs from 'fs';

const program = new Command();

program
  .name('skillguard')
  .description('Security scanner for OpenClaw skill files')
  .version('1.0.0')
  .argument('<path>', 'File or directory to scan')
  .option('-o, --output <file>', 'Save report to file')
  .option('-f, --format <type>', 'Output format: text, json, markdown', 'text')
  .option('-v, --verbose', 'Show detailed findings', false)
  .option('--severity <level>', 'Minimum severity: low, medium, high, critical', 'low')
  .action(async (inputPath, options) => {
    console.log(chalk.bold('\n🔒 SkillGuard Security Scanner\n'));

    if (!fs.existsSync(inputPath)) {
      console.error(chalk.red(`Error: Path not found: ${inputPath}`));
      process.exit(1);
    }

    const stats = fs.statSync(inputPath);
    let results = [];

    if (stats.isDirectory()) {
      console.log(chalk.dim(`Scanning directory: ${inputPath}\n`));
      results = await scanDirectory(inputPath);
    } else {
      console.log(chalk.dim(`Scanning file: ${inputPath}\n`));
      results = [await scanFile(inputPath)];
    }

    const report = formatReport(results, options);

    if (options.output) {
      fs.writeFileSync(options.output, report);
      console.log(chalk.green(`\n✓ Report saved to ${options.output}`));
    } else {
      console.log(report);
    }

    // Exit with error code if critical issues found
    const hasCritical = results.some(r => r.findings.some(f => f.severity === 'critical'));
    process.exit(hasCritical ? 1 : 0);
  });

program.parse();
