const fs = require('fs');
const path = require('path');
const { glob } = require('glob');
const { detectVulnerabilities } = require('./detectors');

async function scanFiles(targetPath) {
  const results = {
    scannedFiles: 0,
    totalIssues: 0,
    findings: [],
    summary: {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0
    }
  };

  // Resolve the path
  const resolvedPath = path.resolve(targetPath);
  
  // Check if it's a file or directory
  const stats = fs.statSync(resolvedPath);
  
  let files = [];
  if (stats.isDirectory()) {
    // Find all .md files in directory
    files = await glob('**/*.md', { cwd: resolvedPath, absolute: true });
  } else if (stats.isFile() && resolvedPath.endsWith('.md')) {
    files = [resolvedPath];
  } else {
    throw new Error('Target must be a .md file or directory containing .md files');
  }

  if (files.length === 0) {
    throw new Error('No .md files found in the specified path');
  }

  // Scan each file
  for (const file of files) {
    const content = fs.readFileSync(file, 'utf-8');
    const fileFindings = detectVulnerabilities(file, content);
    
    results.scannedFiles++;
    results.totalIssues += fileFindings.length;
    
    for (const finding of fileFindings) {
      results.summary[finding.severity]++;
      results.findings.push(finding);
    }
  }

  return results;
}

module.exports = { scanFiles };
