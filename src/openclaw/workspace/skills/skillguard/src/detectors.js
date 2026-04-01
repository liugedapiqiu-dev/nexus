const path = require('path');

// Detection patterns with severity levels
const PATTERNS = {
  // Prompt Injection Patterns
  promptInjection: [
    {
      name: 'Ignore Previous Instructions',
      pattern: /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)/gi,
      severity: 'critical',
      description: 'Attempts to override system instructions'
    },
    {
      name: 'Role Override',
      pattern: /you\s+are\s+(now|actually)\s+a?\s*(different|new|evil|malicious)/gi,
      severity: 'critical',
      description: 'Attempts to change AI role/identity'
    },
    {
      name: 'System Prompt Leak',
      pattern: /(reveal|show|print|output|display)\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)/gi,
      severity: 'high',
      description: 'Attempts to extract system prompt'
    },
    {
      name: 'Jailbreak Attempt',
      pattern: /(DAN|do\s+anything\s+now|jailbreak|bypass\s+restrictions|ignore\s+safety)/gi,
      severity: 'critical',
      description: 'Known jailbreak patterns detected'
    },
    {
      name: 'Delimiter Injection',
      pattern: /(```|<\/?system>|<\/?user>|<\/?assistant>|\[INST\]|\[\/INST\])/gi,
      severity: 'medium',
      description: 'May attempt to inject fake conversation delimiters'
    }
  ],

  // Credential/Secret Patterns
  credentials: [
    {
      name: 'AWS Access Key',
      pattern: /AKIA[0-9A-Z]{16}/g,
      severity: 'critical',
      description: 'AWS Access Key ID detected'
    },
    {
      name: 'AWS Secret Key',
      pattern: /[A-Za-z0-9\/+=]{40}/g,
      severity: 'high',
      description: 'Potential AWS Secret Access Key',
      validator: (match) => match.includes('/') || match.includes('+')
    },
    {
      name: 'GitHub Token',
      pattern: /(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}/g,
      severity: 'critical',
      description: 'GitHub Personal Access Token detected'
    },
    {
      name: 'Generic API Key',
      pattern: /(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["']?[A-Za-z0-9_\-]{20,}["']?/gi,
      severity: 'high',
      description: 'Hardcoded API key detected'
    },
    {
      name: 'Bearer Token',
      pattern: /bearer\s+[A-Za-z0-9_\-\.]+/gi,
      severity: 'high',
      description: 'Bearer token in plaintext'
    },
    {
      name: 'Private Key',
      pattern: /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/g,
      severity: 'critical',
      description: 'Private key embedded in file'
    },
    {
      name: 'Password in Text',
      pattern: /(password|passwd|pwd)\s*[=:]\s*["']?[^\s"']{8,}["']?/gi,
      severity: 'high',
      description: 'Hardcoded password detected'
    },
    {
      name: 'Slack Token',
      pattern: /xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*/g,
      severity: 'critical',
      description: 'Slack API token detected'
    },
    {
      name: 'OpenAI API Key',
      pattern: /sk-[A-Za-z0-9]{32,}/g,
      severity: 'critical',
      description: 'OpenAI API key detected'
    }
  ],

  // Suspicious Commands
  commands: [
    {
      name: 'Curl to External URL',
      pattern: /curl\s+(-[A-Za-z]+\s+)*["']?https?:\/\/(?!localhost|127\.0\.0\.1)[^\s"']+/gi,
      severity: 'medium',
      description: 'External HTTP request via curl'
    },
    {
      name: 'Wget Download',
      pattern: /wget\s+(-[A-Za-z]+\s+)*["']?https?:\/\/[^\s"']+/gi,
      severity: 'medium',
      description: 'File download via wget'
    },
    {
      name: 'Eval Execution',
      pattern: /\beval\s*\(/g,
      severity: 'high',
      description: 'Dynamic code execution via eval()'
    },
    {
      name: 'Shell Execution',
      pattern: /\b(exec|system|popen|subprocess|spawn)\s*\(/gi,
      severity: 'high',
      description: 'Shell command execution'
    },
    {
      name: 'Base64 Decode Pipe',
      pattern: /base64\s+(-d|--decode)\s*\|\s*(sh|bash|zsh|python|node)/gi,
      severity: 'critical',
      description: 'Encoded payload execution pattern'
    },
    {
      name: 'Reverse Shell',
      pattern: /(nc|netcat|ncat)\s+(-[A-Za-z]+\s+)*\d+\.\d+\.\d+\.\d+\s+\d+/gi,
      severity: 'critical',
      description: 'Potential reverse shell connection'
    },
    {
      name: 'Bash Reverse Shell',
      pattern: /bash\s+-i\s+>&?\s*\/dev\/tcp/gi,
      severity: 'critical',
      description: 'Bash reverse shell pattern'
    },
    {
      name: 'Dangerous rm Command',
      pattern: /rm\s+(-rf?|--force)\s+(\/|\*|~)/gi,
      severity: 'high',
      description: 'Dangerous file deletion command'
    },
    {
      name: 'Chmod 777',
      pattern: /chmod\s+777/g,
      severity: 'medium',
      description: 'Overly permissive file permissions'
    },
    {
      name: 'Sudo No Password',
      pattern: /sudo\s+NOPASSWD/gi,
      severity: 'high',
      description: 'Passwordless sudo configuration'
    }
  ],

  // Data Exfiltration Patterns
  exfiltration: [
    {
      name: 'Environment Variable Access',
      pattern: /\$\{?(ENV|HOME|PATH|AWS_|GITHUB_|SECRET|TOKEN|KEY|PASSWORD)[A-Z_]*\}?/g,
      severity: 'medium',
      description: 'Accessing sensitive environment variables'
    },
    {
      name: 'File Read Commands',
      pattern: /cat\s+(\/etc\/passwd|\/etc\/shadow|~\/\.ssh|~\/\.aws)/gi,
      severity: 'high',
      description: 'Reading sensitive system files'
    },
    {
      name: 'SSH Key Access',
      pattern: /\.ssh\/(id_rsa|id_ed25519|authorized_keys)/gi,
      severity: 'high',
      description: 'Accessing SSH keys'
    }
  ]
};

function detectVulnerabilities(filePath, content) {
  const findings = [];
  const lines = content.split('\n');
  const fileName = path.basename(filePath);

  // Run all pattern categories
  for (const [category, patterns] of Object.entries(PATTERNS)) {
    for (const detector of patterns) {
      // Reset regex lastIndex
      detector.pattern.lastIndex = 0;
      
      let match;
      while ((match = detector.pattern.exec(content)) !== null) {
        // If there's a validator, check it
        if (detector.validator && !detector.validator(match[0])) {
          continue;
        }

        // Find line number
        const beforeMatch = content.substring(0, match.index);
        const lineNumber = beforeMatch.split('\n').length;
        const line = lines[lineNumber - 1] || '';

        findings.push({
          file: filePath,
          fileName,
          category,
          name: detector.name,
          severity: detector.severity,
          description: detector.description,
          line: lineNumber,
          column: match.index - beforeMatch.lastIndexOf('\n'),
          match: match[0].substring(0, 100), // Truncate long matches
          context: line.trim().substring(0, 150)
        });
      }
    }
  }

  return findings;
}

module.exports = { detectVulnerabilities, PATTERNS };
