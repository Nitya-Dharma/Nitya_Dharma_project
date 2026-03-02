"""
Security Tests: Infrastructure & Platform-Level Attacks (PART 4)

UNIT 21-27: SSRF, File Upload Abuse, Path Traversal, Insecure Deserialization,
Supply Chain Security, Secrets Exposure, Cloud Metadata Abuse

This module provides test utilities and code review functions for infrastructure
and platform-level security vulnerabilities.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding."""
    severity: str  # 'Critical', 'High', 'Medium', 'Low'
    category: str  # 'SSRF', 'File Upload', etc.
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str


class InfrastructureSecurityTester:
    """Security testing utilities for infrastructure and platform-level attacks."""
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize with project root directory."""
        if project_root is None:
            current = Path(__file__).parent.parent
            if (current / 'manage.py').exists():
                self.project_root = current
            else:
                self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)
    
    def find_ssrf_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 21: Find SSRF (Server-Side Request Forgery) vulnerabilities.
        
        Searches for:
        - Server-side HTTP requests with user-controlled URLs
        - Missing IP/URL validation
        - Cloud metadata access risks
        """
        findings = []
        
        dangerous_patterns = [
            (r'requests\.(get|post|put|delete|patch)\([^)]*url\s*=', 'HTTP request with user-controlled URL'),
            (r'urllib\.(request|urlopen)\([^)]*url\s*=', 'urllib request with user-controlled URL'),
            (r'httpx\.(get|post|put|delete|patch)\([^)]*url\s*=', 'httpx request with user-controlled URL'),
            (r'fetch\([^)]*url\s*=', 'Server-side fetch with user-controlled URL'),
        ]
        
        private_ip_patterns = [
            r'127\.0\.0\.1', r'localhost', r'169\.254\.169\.254',  # Cloud metadata
            r'10\.\d+\.\d+\.\d+', r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+',  # Private ranges
            r'192\.168\.\d+\.\d+', r'\[::1\]',  # IPv6 localhost
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
                            if re.search(pattern, line, re.IGNORECASE):
                                # Check if URL is user-controlled
                                func_start = max(0, i - 50)
                                func_end = min(len(lines), i + 50)
                                
                                has_validation = False
                                user_controlled = False
                                
                                # Check surrounding code
                                for j in range(func_start, func_end):
                                    if any(keyword in lines[j].lower() for keyword in ['request.get', 'request.post', 'request.data', 'request.body', 'url', 'input']):
                                        user_controlled = True
                                    if any(keyword in lines[j].lower() for keyword in ['validate', 'whitelist', 'allowlist', 'block', 'private', 'localhost']):
                                        has_validation = True
                                    # Check for IP validation
                                    if any(ip_pattern in lines[j] for ip_pattern in ['127.0.0', 'localhost', 'private', 'metadata']):
                                        has_validation = True
                                
                                if user_controlled and not has_validation:
                                    findings.append(SecurityFinding(
                                        severity='Critical',
                                        category='SSRF',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description=f"SSRF vulnerability: {description} without validation",
                                        recommendation="Validate URLs: block private IPs (127.0.0.0/8, 10.0.0.0/8, 169.254.0.0/16), use URL allowlist, or validate scheme"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_file_upload_abuse_risks(self) -> List[SecurityFinding]:
        """
        UNIT 22: Find file upload abuse vulnerabilities.
        
        Checks for:
        - Missing file extension validation
        - Missing MIME type validation
        - Unsafe file storage
        - Executable file uploads
        """
        findings = []
        
        dangerous_extensions = ['.php', '.jsp', '.asp', '.exe', '.sh', '.bat', '.cmd', '.js', '.html']
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for file upload patterns
                    for i, line in enumerate(lines, 1):
                        if re.search(r'\.(FILES|files|upload)', line) or 'request.FILES' in line:
                            func_start = max(0, i - 100)
                            func_end = min(len(lines), i + 100)
                            
                            has_extension_check = False
                            has_mime_check = False
                            has_allowlist = False
                            
                            # Check for validation
                            for j in range(func_start, func_end):
                                if any(keyword in lines[j].lower() for keyword in ['extension', 'ext', 'suffix', 'endswith']):
                                    has_extension_check = True
                                if any(keyword in lines[j].lower() for keyword in ['mime', 'content_type', 'content-type']):
                                    has_mime_check = True
                                if any(keyword in lines[j].lower() for keyword in ['allowlist', 'whitelist', 'allowed', 'permitted']):
                                    has_allowlist = True
                                # Check for blocklist (bad practice)
                                if any(keyword in lines[j].lower() for keyword in ['blocklist', 'blacklist', 'forbidden', 'denied']):
                                    findings.append(SecurityFinding(
                                        severity='High',
                                        category='File Upload',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=j,
                                        code_snippet=lines[j].strip(),
                                        description="File upload uses blocklist (insecure) - should use allowlist",
                                        recommendation="Replace blocklist with allowlist of permitted extensions and MIME types"
                                    ))
                            
                            if not has_extension_check or not has_allowlist:
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='File Upload',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="File upload without proper validation - missing extension allowlist or MIME validation",
                                    recommendation="Add extension allowlist (not blocklist), MIME type validation, and store files outside web root"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_path_traversal_risks(self) -> List[SecurityFinding]:
        """
        UNIT 23: Find path traversal vulnerabilities.
        
        Checks for:
        - User input used in file paths
        - Missing path normalization
        - Directory traversal possible
        """
        findings = []
        
        dangerous_patterns = [
            (r'open\([^)]*\+.*request\.', 'File open with user input'),
            (r'os\.path\.join\([^)]*request\.', 'os.path.join with user input without validation'),
            (r'Path\([^)]*\+.*request\.', 'Path construction with user input'),
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
                            if re.search(pattern, line, re.IGNORECASE):
                                func_start = max(0, i - 50)
                                func_end = min(len(lines), i + 50)
                                
                                has_validation = False
                                
                                # Check for path normalization
                                for j in range(func_start, func_end):
                                    if any(keyword in lines[j].lower() for keyword in ['normalize', 'resolve', 'realpath', 'abspath', 'basename']):
                                        has_validation = True
                                    if '..' in lines[j] and ('block' in lines[j].lower() or 'reject' in lines[j].lower()):
                                        has_validation = True
                                
                                if not has_validation:
                                    findings.append(SecurityFinding(
                                        severity='Critical',
                                        category='Path Traversal',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description=f"Path traversal risk: {description}",
                                        recommendation="Use os.path.normpath(), validate path doesn't contain '..', use fixed base directories"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_insecure_deserialization_risks(self) -> List[SecurityFinding]:
        """
        UNIT 24: Find insecure deserialization vulnerabilities.
        
        Checks for:
        - pickle.loads() on user input
        - yaml.load() instead of yaml.safe_load()
        - eval() usage
        """
        findings = []
        
        dangerous_patterns = [
            (r'pickle\.loads?\([^)]*request\.', 'pickle.loads with user input'),
            (r'pickle\.loads?\([^)]*data', 'pickle.loads with potentially untrusted data'),
            (r'yaml\.load\(', 'yaml.load (unsafe) - should use yaml.safe_load'),
            (r'eval\([^)]*request\.', 'eval with user input'),
            (r'exec\([^)]*request\.', 'exec with user input'),
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
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='Insecure Deserialization',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Insecure deserialization: {description}",
                                    recommendation="Use safe alternatives: yaml.safe_load(), json.loads(), or explicit schema-based deserialization. Never use pickle.loads() on untrusted data"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_supply_chain_risks(self) -> List[SecurityFinding]:
        """
        UNIT 25: Find supply chain security risks.
        
        Checks for:
        - Unpinned dependencies
        - Wildcard versions
        - External CDNs without integrity
        """
        findings = []
        
        # Check requirements.txt
        requirements_file = self.project_root / 'requirements.txt'
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # Check for wildcard versions
                        if '==' not in line and '>=' not in line and '~=' not in line:
                            if not line.startswith('-') and 'git+' not in line:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Supply Chain',
                                    file_path=str(requirements_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line,
                                    description="Unpinned dependency version",
                                    recommendation="Pin dependency versions (use ==, >=, or ~=) to prevent unexpected updates"
                                ))
            except Exception:
                pass
        
        # Check for external CDNs in templates
        for html_file in self.project_root.rglob('*.html'):
            file_str = str(html_file)
            if any(skip in file_str for skip in ['venv', 'site-packages', '__pycache__']):
                continue
            
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Check for external CDN scripts without integrity
                        if re.search(r'<script[^>]*src=["\']https?://', line, re.IGNORECASE):
                            if 'integrity=' not in line and 'crossorigin=' not in line:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Supply Chain',
                                    file_path=str(html_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="External CDN script without integrity check",
                                    recommendation="Add integrity and crossorigin attributes to external scripts for Subresource Integrity (SRI)"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_secrets_exposure_risks(self) -> List[SecurityFinding]:
        """
        UNIT 26: Find secrets exposure vulnerabilities.
        
        Checks for:
        - Hardcoded API keys
        - Hardcoded passwords
        - Secrets in code
        - DEBUG=True in production
        """
        findings = []
        
        secret_patterns = [
            (r'API[_\s]*KEY[_\s]*=["\']\w+', 'Hardcoded API key'),
            (r'SECRET[_\s]*KEY[_\s]*=["\']\w+', 'Hardcoded secret key'),
            (r'PASSWORD[_\s]*=["\']\w+', 'Hardcoded password'),
            (r'TOKEN[_\s]*=["\']\w+', 'Hardcoded token'),
            (r'DEBUG\s*=\s*True', 'DEBUG enabled (should be False in production)'),
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
                        for pattern, description in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                # Skip if it's getting from environment
                                if 'os.environ' in line or 'os.getenv' in line or 'getenv' in line:
                                    continue
                                # Skip if it's a comment
                                if line.strip().startswith('#'):
                                    continue
                                
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='Secrets Exposure',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Secrets exposure: {description}",
                                    recommendation="Move secrets to environment variables. Never hardcode credentials in code"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_cloud_metadata_risks(self) -> List[SecurityFinding]:
        """
        UNIT 27: Find cloud metadata and IAM abuse risks.
        
        Checks for:
        - Cloud metadata URLs in code
        - Potential SSRF chains to metadata
        """
        findings = []
        
        metadata_urls = [
            '169.254.169.254',  # AWS, GCP, Azure metadata
            'metadata.google.internal',
            'metadata.azure.com',
            '169.254.169.254/latest/meta-data',
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
                        for metadata_url in metadata_urls:
                            if metadata_url in line.lower():
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='Cloud Metadata',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Cloud metadata URL reference: {metadata_url}",
                                    recommendation="Ensure metadata access is blocked. If needed, use IAM roles with least privilege, never expose metadata endpoints"
                                ))
            except Exception:
                continue
        
        return findings
    
    def generate_test_report(self) -> str:
        """Generate comprehensive security test report."""
        report = []
        report.append("=" * 80)
        report.append("SECURITY TEST REPORT - INFRASTRUCTURE & PLATFORM ATTACKS (PART 4)")
        report.append("=" * 80)
        report.append("")
        
        # Run all tests
        ssrf_findings = self.find_ssrf_vulnerabilities()
        file_upload_findings = self.find_file_upload_abuse_risks()
        path_traversal_findings = self.find_path_traversal_risks()
        deserialization_findings = self.find_insecure_deserialization_risks()
        supply_chain_findings = self.find_supply_chain_risks()
        secrets_findings = self.find_secrets_exposure_risks()
        cloud_metadata_findings = self.find_cloud_metadata_risks()
        
        all_findings = (
            ssrf_findings + file_upload_findings + path_traversal_findings +
            deserialization_findings + supply_chain_findings + secrets_findings +
            cloud_metadata_findings
        )
        
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
    Run all PART 4 security tests and return report and findings.
    
    Usage:
        report, findings = run_security_tests()
        print(report)
    """
    tester = InfrastructureSecurityTester(project_root)
    report = tester.generate_test_report()
    
    # Collect all findings
    all_findings = (
        tester.find_ssrf_vulnerabilities() +
        tester.find_file_upload_abuse_risks() +
        tester.find_path_traversal_risks() +
        tester.find_insecure_deserialization_risks() +
        tester.find_supply_chain_risks() +
        tester.find_secrets_exposure_risks() +
        tester.find_cloud_metadata_risks()
    )
    
    return report, all_findings


if __name__ == '__main__':
    # Run tests when executed directly
    report, findings = run_security_tests()
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent.parent / 'SECURITY_TEST_REPORT_PART4.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")




















