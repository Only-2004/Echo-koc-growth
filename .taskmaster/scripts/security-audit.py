#!/usr/bin/env python3
"""基于代码库扫描自动生成安全检查清单。"""
import json, os, re, sys
from pathlib import Path

def scan_patterns():
    """扫描代码库中与安全相关的模式。"""
    findings = []
    cwd = Path(".")

    # 侦测模式
    patterns = {
        "authentication": r"(password|login|auth|session|jwt|token)",
        "database": r"(sql|query|SELECT|INSERT|UPDATE|DELETE|prisma|sequelize|knex)",
        "api": r"(api|endpoint|route|controller|express|fastapi|flask)",
        "encryption": r"(encrypt|decrypt|hash|bcrypt|crypto|aes)",
        "file_upload": r"(upload|multipart|formdata|file.*input)",
        "environment": r"(process\.env|os\.environ|dotenv|\.env)",
    }

    for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"]:
        for f in cwd.rglob(ext):
            if ".git" in str(f) or "node_modules" in str(f) or ".taskmaster" in str(f):
                continue
            try:
                content = f.read_text(errors="ignore")
                for category, pattern in patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({"file": str(f), "category": category})
            except Exception:
                pass

    categories = list(set(f["category"] for f in findings))

    checklist = []
    if "authentication" in categories:
        checklist.extend([
            "密码使用 bcrypt 哈希（cost >= 10）",
            "会话 token 使用加密安全的随机源",
            "在身份验证接口启用限流",
        ])
    if "database" in categories:
        checklist.extend([
            "所有查询使用参数化语句",
            "无 SQL 注入漏洞",
            "数据库凭据不硬编码在源代码中",
        ])
    if "api" in categories:
        checklist.extend([
            "生产环境强制 HTTPS",
            "启用 CSRF 防护",
            "所有接口进行输入校验",
            "设置安全响应头（CSP、X-Frame-Options）",
        ])
    if "encryption" in categories:
        checklist.extend([
            "使用强加密算法（如 AES-256）",
            "密钥安全存储（不硬编码）",
        ])
    if "environment" in categories:
        checklist.extend([
            ".env 文件已加入 .gitignore",
            "未将机密信息提交到仓库",
        ])

    # 始终包含
    checklist.extend([
        "依赖已做漏洞扫描（npm audit / pip audit）",
        "错误信息不泄露内部细节",
    ])

    print(json.dumps({
        "ok": True,
        "categories_detected": categories,
        "findings_count": len(findings),
        "checklist": checklist,
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    scan_patterns()
