import fs from 'fs';
import path from 'path';
import chalk from 'chalk';

// Security patterns to detect
const PATTERNS = {
  critical: [
    { name: 'API Key Exposure', pattern: /(?:api[_-]?key|apikey|secret[_-]?key|auth[_-]?token)\s*[:=]\s*['"][^'"]{10,}['"]/gi, desc: 'Hardcoded API key or secret detected' },
    { name: 'Credential Leak', pattern: /(?:password|passwd|pwd)\s*[:=]\s*['"][^'"]+['"]/gi, desc: 'Hardcoded password detected' },
    { name: 'Private Key', pattern: /-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----/g, desc: 'Private key embedded in file' },
    { name: 'Shell Injection', pattern: /exec\s*\(\s*[`'"].*\$\{/g, desc: 'Potential shell injection via template literals' },
  ],
  high: [
    { name: 'Prompt Injection', pattern: /ignore (?:all |previous |above )?instructions?|forget (?:everything|all|previous)/gi, desc: 'Prompt injection attempt detected' },
    { name: 'Data Exfiltration', pattern: /curl\s+.*(?:webhook|ngrok|requestbin|pipedream)/gi, desc: 'Suspicious data exfiltration to external service' },
    { name: 'Eval Usage', pattern: /\beval\s*\(/g, desc: 'Dangerous eval() usage detected' },
    { name: 'Base64 Decode Execute', pattern: /atob\s*\(|Buffer\.from\([^)]+,\s*['"]base64['"]\)/g, desc: 'Base64 decoding (potential obfuscation)' },
    { name: 'Environment Access', pattern: /process\.env\[?['"]/g, desc: 'Direct environment variable access' },
  ],
  medium: [
    { name: 'External URL', pattern: /https?:\/\/(?!github\.com|npmjs\.com|localhost)[^\s'")\]]+/g, desc: 'External URL reference (verify legitimacy)' },
    { name: 'File System Write', pattern: /fs\.(?:writeFile|appendFile|createWriteStream)/g, desc: 'File system write operation' },
    { name: 'Network Request', pattern: /(?:fetch|axios|request)\s*\(/g, desc: 'Network request detected' },
    { name: 'Child Process', pattern: /child_process|spawn|execSync|execFile/g, desc: 'Child process execution' },
  ],
  low: [
    { name: 'TODO Security', pattern: /TODO:?\s*(?:security|fix|hack|temp)/gi, desc: 'Security-related TODO comment' },
    { name: 'Console Log', pattern: /console\.log\s*\(/g, desc: 'Console logging (may leak sensitive data)' },
    { name: 'Disabled Validation', pattern: /validate\s*[:=]\s*false|skipValidation/gi, desc: 'Validation may be disabled' },
  ]
};

export async function scanFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const findings = [];

  for (const [severity, patterns] of Object.entries(PATTERNS)) {
    for (const { name, pattern, desc } of patterns) {
      const matches = content.match(pattern);
      if (matches) {
        findings.push({
          severity,
          name,
          description: desc,
          count: matches.length,
          file: filePath,
          samples: matches.slice(0, 3).map(m => m.substring(0, 50) + (m.length > 50 ? '...' : ''))
        });
      }
    }
  }

  return {
    file: filePath,
    findings,
    score: calculateScore(findings)
  };
}

export async function scanDirectory(dirPath) {
  const results = [];
  const files = fs.readdirSync(dirPath, { withFileTypes: true });

  for (const file of files) {
    const fullPath = path.join(dirPath, file.name);
    
    if (file.isDirectory()) {
      if (!['node_modules', '.git', 'dist', 'build'].includes(file.name)) {
        results.push(...await scanDirectory(fullPath));
      }
    } else if (file.name.endsWith('.md') || file.name.endsWith('.js') || file.name.endsWith('.ts')) {
      results.push(await scanFile(fullPath));
    }
  }

  return results;
}

function calculateScore(findings) {
  const weights = { critical: 100, high: 25, medium: 5, low: 1 };
  const total = findings.reduce((sum, f) => sum + (weights[f.severity] || 0) * f.count, 0);
  return Math.max(0, 100 - total);
}

export function formatReport(results, options) {
  const severityColors = {
    critical: chalk.red.bold,
    high: chalk.red,
    medium: chalk.yellow,
    low: chalk.dim
  };

  const severityOrder = ['critical', 'high', 'medium', 'low'];
  const minSeverityIndex = severityOrder.indexOf(options.severity || 'low');

  let output = '';
  let totalFindings = 0;
  let criticalCount = 0;

  for (const result of results) {
    const filteredFindings = result.findings.filter(
      f => severityOrder.indexOf(f.severity) <= minSeverityIndex
    );

    if (filteredFindings.length === 0) continue;

    output += chalk.bold(`\n📄 ${result.file}\n`);
    output += chalk.dim(`   Security Score: ${result.score}/100\n\n`);

    for (const finding of filteredFindings) {
      const color = severityColors[finding.severity];
      const icon = finding.severity === 'critical' ? '🚨' : 
                   finding.severity === 'high' ? '⚠️' : 
                   finding.severity === 'medium' ? '⚡' : 'ℹ️';
      
      output += `   ${icon} ${color(`[${finding.severity.toUpperCase()}]`)} ${finding.name}\n`;
      output += chalk.dim(`      ${finding.description}\n`);
      output += chalk.dim(`      Found ${finding.count} occurrence(s)\n`);
      
      if (options.verbose && finding.samples.length > 0) {
        output += chalk.dim(`      Samples:\n`);
        finding.samples.forEach(s => {
          output += chalk.dim(`        - ${s}\n`);
        });
      }
      output += '\n';

      totalFindings += finding.count;
      if (finding.severity === 'critical') criticalCount += finding.count;
    }
  }

  // Summary
  output += chalk.bold('\n' + '─'.repeat(50) + '\n');
  output += chalk.bold('📊 Summary\n\n');
  output += `   Files scanned: ${results.length}\n`;
  output += `   Total findings: ${totalFindings}\n`;
  
  if (criticalCount > 0) {
    output += chalk.red.bold(`\n   ⛔ ${criticalCount} CRITICAL issue(s) found!\n`);
  } else if (totalFindings === 0) {
    output += chalk.green('\n   ✓ No security issues detected\n');
  }

  return output;
}
