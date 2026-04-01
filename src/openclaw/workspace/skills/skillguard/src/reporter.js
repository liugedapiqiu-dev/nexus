const chalk = require('chalk');

const SEVERITY_COLORS = {
  critical: chalk.bgRed.white.bold,
  high: chalk.red.bold,
  medium: chalk.yellow,
  low: chalk.blue
};

const SEVERITY_ICONS = {
  critical: '🚨',
  high: '⚠️ ',
  medium: '⚡',
  low: 'ℹ️ '
};

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'];

function generateReport(results, options) {
  const { output, severity } = options;
  
  // Filter by minimum severity
  const severityIndex = SEVERITY_ORDER.indexOf(severity);
  const filteredFindings = results.findings.filter(f => 
    SEVERITY_ORDER.indexOf(f.severity) <= severityIndex
  );

  if (output === 'json') {
    console.log(JSON.stringify({ ...results, findings: filteredFindings }, null, 2));
    return;
  }

  // Text output
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.white.bold(`📁 Files scanned: ${results.scannedFiles}`));
  console.log(chalk.white.bold(`🔍 Issues found:  ${filteredFindings.length}`));
  console.log(chalk.gray('─'.repeat(60)));

  // Summary by severity
  console.log('\n' + chalk.white.bold('Summary by Severity:'));
  console.log(`  ${SEVERITY_ICONS.critical} Critical: ${SEVERITY_COLORS.critical(` ${results.summary.critical} `)}`);
  console.log(`  ${SEVERITY_ICONS.high} High:     ${SEVERITY_COLORS.high(results.summary.high)}`);
  console.log(`  ${SEVERITY_ICONS.medium} Medium:   ${SEVERITY_COLORS.medium(results.summary.medium)}`);
  console.log(`  ${SEVERITY_ICONS.low} Low:      ${SEVERITY_COLORS.low(results.summary.low)}`);

  if (filteredFindings.length === 0) {
    console.log(chalk.green.bold('\n✅ No security issues found!\n'));
    return;
  }

  // Group findings by file
  const byFile = {};
  for (const finding of filteredFindings) {
    if (!byFile[finding.file]) {
      byFile[finding.file] = [];
    }
    byFile[finding.file].push(finding);
  }

  // Print findings
  console.log('\n' + chalk.white.bold('Detailed Findings:\n'));

  for (const [file, findings] of Object.entries(byFile)) {
    console.log(chalk.cyan.bold(`\n📄 ${file}`));
    console.log(chalk.gray('─'.repeat(60)));

    // Sort by severity
    findings.sort((a, b) => 
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
    );

    for (const f of findings) {
      const severityBadge = SEVERITY_COLORS[f.severity](` ${f.severity.toUpperCase()} `);
      console.log(`\n  ${SEVERITY_ICONS[f.severity]} ${severityBadge} ${chalk.white.bold(f.name)}`);
      console.log(chalk.gray(`     Category: ${f.category}`));
      console.log(chalk.gray(`     Line ${f.line}: ${f.context}`));
      console.log(chalk.gray(`     → ${f.description}`));
    }
  }

  // Exit code based on severity
  console.log('\n' + chalk.gray('─'.repeat(60)));
  
  if (results.summary.critical > 0) {
    console.log(chalk.red.bold('\n❌ CRITICAL issues found - immediate action required!\n'));
    process.exitCode = 2;
  } else if (results.summary.high > 0) {
    console.log(chalk.yellow.bold('\n⚠️  HIGH severity issues found - review recommended\n'));
    process.exitCode = 1;
  } else {
    console.log(chalk.green('\n✓ No critical/high severity issues\n'));
  }
}

module.exports = { generateReport };
