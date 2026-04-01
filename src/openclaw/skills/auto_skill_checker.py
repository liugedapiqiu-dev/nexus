#!/usr/bin/env python3
"""
技能配置自动检查器
检查所有 OpenClaw 技能的配置完整性，自动报告缺失的 skill.json 或 SKILL.md
"""

import os
import json
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".openclaw" / "skills"
REPORT_PATH = Path.home() / ".openclaw" / "workspace" / "memory" / "skill_check_report.md"

def check_skill_integrity():
    """检查所有技能的配置完整性"""
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_skills": 0,
        "complete": [],
        "missing_json": [],
        "missing_skillmd": [],
        "missing_both": [],
        "disabled": []
    }
    
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_name = skill_dir.name
        results["total_skills"] += 1
        
        has_json = (skill_dir / "skill.json").exists()
        has_skillmd = (skill_dir / "SKILL.md").exists()
        
        # 检查是否已禁用
        if "disabled" in skill_name.lower():
            results["disabled"].append(skill_name)
            continue
        
        # 分类统计
        if not has_json and not has_skillmd:
            results["missing_both"].append(skill_name)
        elif not has_json:
            results["missing_json"].append(skill_name)
        elif not has_skillmd:
            results["missing_skillmd"].append(skill_name)
        else:
            results["complete"].append(skill_name)
    
    return results

def generate_report(results):
    """生成检查报告"""
    
    complete_rate = (len(results["complete"]) / results["total_skills"] * 100) if results["total_skills"] > 0 else 0
    
    report = f"""# 技能配置完整性检查报告

**检查时间:** {results["timestamp"]}
**技能总数:** {results["total_skills"]}
**完整配置率:** {complete_rate:.1f}%

---

## ✅ 配置完整的技能 ({len(results["complete"])})

{chr(10).join([f"- {skill}" for skill in results["complete"]])}

---

## ⚠️ 配置缺失的技能

### 缺少 skill.json ({len(results["missing_json"])})

{chr(10).join([f"- {skill}" for skill in results["missing_json"]]) or "无"}

### 缺少 SKILL.md ({len(results["missing_skillmd"])})

{chr(10).join([f"- {skill}" for skill in results["missing_skillmd"]]) or "无"}

### 两者都缺失 ({len(results["missing_both"])})

{chr(10).join([f"- {skill}" for skill in results["missing_both"]]) or "无"}

---

## 🚫 已禁用的技能 ({len(results["disabled"])})

{chr(10).join([f"- {skill}" for skill in results["disabled"]]) or "无"}

---

## 🔧 建议操作

"""
    
    # 生成自动修复建议
    if results["missing_json"] or results["missing_skillmd"] or results["missing_both"]:
        report += """### 自动修复命令

```bash
# 为缺失配置的技能创建模板
python3 ~/.openclaw/skills/auto_skill_fixer.py
```

### 手动修复

1. 为缺少 skill.json 的技能创建配置文件
2. 为缺少 SKILL.md 的技能创建文档
3. 考虑移除或启用已禁用的技能
"""
    else:
        report += """**所有技能配置完整！无需操作！** ✅
"""
    
    return report

def auto_fix():
    """自动创建缺失的配置模板"""
    results = check_skill_integrity()
    
    fixed = []
    
    for skill_name in results["missing_json"]:
        skill_dir = SKILLS_DIR / skill_name
        json_path = skill_dir / "skill.json"
        
        # 创建基础 skill.json 模板
        template = {
            "name": skill_name,
            "description": f"{skill_name} 技能",
            "version": "1.0.0",
            "author": "OpenClaw Community",
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "triggers": {
                "intent": [f"{skill_name} 相关操作"]
            },
            "entry": {
                "type": "script",
                "path": "./"
            },
            "examples": [
                f"使用 {skill_name} 技能"
            ]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        fixed.append(f"{skill_name}/skill.json")
    
    for skill_name in results["missing_skillmd"]:
        skill_dir = SKILLS_DIR / skill_name
        md_path = skill_dir / "SKILL.md"
        
        # 创建基础 SKILL.md 模板
        template = f"""---
name: {skill_name}
description: {skill_name} 技能
version: 1.0.0
metadata:
---

# {skill_name} 技能

## 功能描述

（在此描述技能的功能）

## 使用方法

（在此描述如何使用）

## 示例

（在此提供使用示例）

---

*Made with ❤️ for OpenClaw Community*
"""
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        fixed.append(f"{skill_name}/SKILL.md")
    
    return fixed

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-fix":
        print("🔧 自动修复模式")
        fixed = auto_fix()
        print(f"✅ 已修复 {len(fixed)} 个配置文件:")
        for file in fixed:
            print(f"   - {file}")
    else:
        print("🔍 技能配置完整性检查")
        results = check_skill_integrity()
        report = generate_report(results)
        
        # 输出报告
        print(report)
        
        # 保存报告
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 报告已保存至：{REPORT_PATH}")
