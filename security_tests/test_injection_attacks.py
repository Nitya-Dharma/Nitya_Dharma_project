"""
Security Tests: Injection Attacks (PART 1)

UNIT 1-6: SQL Injection, NoSQL Injection, XSS, Command Injection

This module provides test utilities and code review functions for injection vulnerabilities.
"""

import re
import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding."""
    severity: str  # 'Critical', 'High', 'Medium', 'Low'
    category: str  # 'SQL Injection', 'XSS', etc.
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str


class InjectionSecurityTester:
    """Security testing utilities for injection attacks."""
    
    # SQL Injection payloads (2026-relevant)
    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        '" OR "1"="1',
        "' UNION SELECT NULL, NULL--",
        "' OR SLEEP(10)--",
        "1; WAITFOR DELAY '00:00:10'--",
        "%27%20OR%201%3D1--",
        "admin'--",
        "admin'/*",
        "' OR 1=1#",
        "' OR 'a'='a",
    ]
    
    # NoSQL Injection payloads
    NOSQL_INJECTION_PAYLOADS = [
        {"email": {"$ne": None}, "password": {"$ne": None}},
        {"$where": "this.password.length > 0"},
        {"email": {"$regex": ".*"}},
        {"$gt": ""},
    ]
    
    # XSS payloads
    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        "<iframe src=javascript:alert(1)>",
        "<body onload=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
        "<select onfocus=alert(1) autofocus>",
        "<textarea onfocus=alert(1) autofocus>",
        "<keygen onfocus=alert(1) autofocus>",
        "<video><source onerror=alert(1)>",
        "<audio src=x onerror=alert(1)>",
        "<details open ontoggle=alert(1)>",
        "<marquee onstart=alert(1)>",
        "<div onmouseover=alert(1)>",
        "<style>@import'javascript:alert(1)';</style>",
    ]
    
    # Command Injection payloads
    COMMAND_INJECTION_PAYLOADS = [
        "; ls",
        "&& whoami",
        "| cat /etc/passwd",
        "; rm -rf /",
        "`whoami`",
        "$(whoami)",
        "; ping -c 4 127.0.0.1",
        "&& echo 'test'",
    ]
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize with project root directory."""
        if project_root is None:
            # Try to find project root
            current = Path(__file__).parent.parent
            if (current / 'manage.py').exists():
                self.project_root = current
            else:
                self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)
    
    def find_raw_sql_queries(self) -> List[SecurityFinding]:
        """
        UNIT 1: Find potential SQL Injection vulnerabilities.
        
        Searches for:
        - Raw SQL queries using cursor.execute()
        - String formatting in queries
        - User input directly in SQL
        """
        findings = []
        
        # Patterns to search for
        dangerous_patterns = [
            (r'cursor\.execute\s*\([^)]*\+', 'String concatenation in cursor.execute'),
            (r'cursor\.execute\s*\([^)]*%', 'String formatting in cursor.execute'),
            (r'cursor\.execute\s*\([^)]*\.format\(', 'String format in cursor.execute'),
            (r'cursor\.execute\s*\([^)]*f["\']', 'F-string in cursor.execute'),
            (r'\.raw\s*\([^)]*\+', 'String concatenation in raw()'),
            (r'\.extra\s*\([^)]*\+', 'String concatenation in extra()'),
        ]
        
        # Search Python files
        for py_file in self.project_root.rglob('*.py'):
            # Skip test files, migrations, and third-party libraries
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line):
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='SQL Injection',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Potential SQL injection: {description}",
                                    recommendation="Use parameterized queries with tuple(params) or Django ORM"
                                ))
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return findings
    
    def find_nosql_injection_risks(self) -> List[SecurityFinding]:
        """
        UNIT 2: Find NoSQL Injection vulnerabilities.
        
        Searches for:
        - Direct JSON parsing from user input
        - MongoDB-style query operators from user input
        """
        findings = []
        
        dangerous_patterns = [
            (r'json\.loads\s*\([^)]*request\.', 'JSON parsing from request without validation'),
            (r'\.find\s*\([^)]*request\.', 'MongoDB find with request data'),
            (r'\$\w+\s*:\s*request\.', 'NoSQL operator from request'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line):
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='NoSQL Injection',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Potential NoSQL injection: {description}",
                                    recommendation="Validate and sanitize JSON input, whitelist allowed operators"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_xss_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 3-5: Find XSS vulnerabilities (Stored, Reflected, DOM-based).
        
        Searches for:
        - |safe filter usage in templates
        - mark_safe() in Python code
        - innerHTML / dangerouslySetInnerHTML in JS
        - User input rendered without escaping
        """
        findings = []
        
        # Template files - check for |safe
        for template_file in self.project_root.rglob('*.html'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Check for |safe filter
                        if '|safe' in line and '{{' in line:
                            # Check if it's tracking/analytics (which might be intentional)
                            if 'tracking' not in line.lower() and 'schema' not in line.lower():
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='XSS (Stored/Reflected)',
                                    file_path=str(template_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Template uses |safe filter - potential XSS if user input is rendered",
                                    recommendation="Remove |safe or ensure input is sanitized. Use autoescape=True"
                                ))
            except Exception:
                continue
        
        # Python files - check for mark_safe
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        if 'mark_safe' in line:
                            findings.append(SecurityFinding(
                                severity='High',
                                category='XSS',
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=i,
                                code_snippet=line.strip(),
                                description="mark_safe() used - ensure input is sanitized",
                                recommendation="Verify input is sanitized before using mark_safe()"
                            ))
            except Exception:
                continue
        
        # JavaScript files - check for DOM XSS
        for js_file in self.project_root.rglob('*.js'):
            file_str = str(js_file)
            if any(skip in file_str for skip in ['venv', 'site-packages', 'node_modules', '__pycache__']):
                continue
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        dangerous_patterns = [
                            (r'\.innerHTML\s*=', 'innerHTML assignment'),
                            (r'document\.write\s*\(', 'document.write'),
                            (r'eval\s*\(', 'eval() usage'),
                            (r'dangerouslySetInnerHTML', 'React dangerouslySetInnerHTML'),
                        ]
                        
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line):
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='DOM-based XSS',
                                    file_path=str(js_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Potential DOM XSS: {description}",
                                    recommendation="Sanitize user input before DOM insertion. Use textContent instead of innerHTML"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_command_injection_risks(self) -> List[SecurityFinding]:
        """
        UNIT 6: Find Command Injection vulnerabilities.
        
        Searches for:
        - os.system()
        - subprocess with shell=True
        - exec() / eval()
        - User input in system calls
        """
        findings = []
        
        dangerous_patterns = [
            (r'os\.system\s*\(', 'os.system() usage'),
            (r'subprocess\.\w+\s*\([^)]*shell\s*=\s*True', 'subprocess with shell=True'),
            (r'exec\s*\(', 'exec() usage'),
            (r'eval\s*\(', 'eval() usage'),
            (r'compile\s*\([^)]*request\.', 'compile() with request data'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line):
                                # Check if user input is used
                                if 'request.' in line or 'input(' in line:
                                    severity = 'Critical'
                                else:
                                    severity = 'High'
                                
                                findings.append(SecurityFinding(
                                    severity=severity,
                                    category='Command Injection',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Potential command injection: {description}",
                                    recommendation="Use subprocess with shell=False and list arguments. Never pass user input to shell"
                                ))
            except Exception:
                continue
        
        return findings
    
    def verify_orm_usage(self) -> List[SecurityFinding]:
        """
        Verify that Django ORM is used correctly (parameterized queries).
        
        Checks for proper ORM usage patterns.
        """
        findings = []
        
        # Check for proper parameterized queries in raw SQL
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for cursor.execute with tuple(params) - this is safe
                    if 'cursor.execute' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'cursor.execute' in line:
                                # Check if it uses parameterized queries
                                if 'tuple(' in line or '%s' in line or '?' in line:
                                    # This is likely safe - parameterized
                                    continue
                                elif '+' in line or '%' in line or '.format' in line:
                                    # This is unsafe
                                    findings.append(SecurityFinding(
                                        severity='Critical',
                                        category='SQL Injection',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description="cursor.execute() without parameterized queries",
                                        recommendation="Use parameterized queries: cursor.execute(sql, tuple(params))"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def generate_test_report(self) -> str:
        """Generate comprehensive security test report."""
        report = []
        report.append("=" * 80)
        report.append("SECURITY TEST REPORT - INJECTION ATTACKS (PART 1)")
        report.append("=" * 80)
        report.append("")
        
        # Run all tests
        sql_findings = self.find_raw_sql_queries()
        nosql_findings = self.find_nosql_injection_risks()
        xss_findings = self.find_xss_vulnerabilities()
        cmd_findings = self.find_command_injection_risks()
        orm_findings = self.verify_orm_usage()
        
        all_findings = sql_findings + nosql_findings + xss_findings + cmd_findings + orm_findings
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Findings: {len(all_findings)}")
        report.append(f"  Critical: {len([f for f in all_findings if f.severity == 'Critical'])}")
        report.append(f"  High: {len([f for f in all_findings if f.severity == 'High'])}")
        report.append(f"  Medium: {len([f for f in all_findings if f.severity == 'Medium'])}")
        report.append(f"  Low: {len([f for f in all_findings if f.severity == 'Low'])}")
        report.append("")
        
        # Group by category
        by_category = {}
        for finding in all_findings:
            if finding.category not in by_category:
                by_category[finding.category] = []
            by_category[finding.category].append(finding)
        
        # Detailed findings
        for category, findings in by_category.items():
            report.append(f"\n{category.upper()}")
            report.append("-" * 80)
            
            for finding in findings:
                report.append(f"\n[{finding.severity}] {finding.file_path}:{finding.line_number}")
                report.append(f"  Description: {finding.description}")
                report.append(f"  Code: {finding.code_snippet}")
                report.append(f"  Recommendation: {finding.recommendation}")
        
        report.append("\n" + "=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)


def run_security_tests(project_root: Optional[str] = None) -> Tuple[str, List[SecurityFinding]]:
    """
    Run all security tests and return report and findings.
    
    Usage:
        report, findings = run_security_tests()
        print(report)
    """
    tester = InjectionSecurityTester(project_root)
    report = tester.generate_test_report()
    
    # Collect all findings
    all_findings = (
        tester.find_raw_sql_queries() +
        tester.find_nosql_injection_risks() +
        tester.find_xss_vulnerabilities() +
        tester.find_command_injection_risks() +
        tester.verify_orm_usage()
    )
    
    return report, all_findings


if __name__ == '__main__':
    # Run tests when executed directly
    report, findings = run_security_tests()
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent.parent / 'SECURITY_TEST_REPORT_PART1.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")

