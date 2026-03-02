"""
Security Tests: API Abuse, BOLA/IDOR, Rate-Limit Bypass (PART 3)

UNIT 14-20: BOLA, IDOR, Rate-Limit Bypass, Mass Assignment,
Pagination Enumeration, Object State Manipulation, HTTP Verb Tampering

This module provides test utilities and code review functions for API
security vulnerabilities.
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
    category: str  # 'BOLA', 'IDOR', etc.
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str


class APIAbuseSecurityTester:
    """Security testing utilities for API abuse and authorization attacks."""
    
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
    
    def find_bola_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 14: Find BOLA (Broken Object Level Authorization) vulnerabilities.
        
        Searches for:
        - Direct object access without ownership checks
        - Missing request.user filtering
        - ID-based access without authorization
        """
        findings = []
        
        dangerous_patterns = [
            (r'\.objects\.get\([^)]*id\s*=\s*[^)]*request\.', 'Direct object access with request ID without ownership check'),
            (r'\.objects\.filter\([^)]*id\s*=\s*[^)]*request\.', 'Filter by request ID without user scope'),
            (r'get_object_or_404\([^,]+,\s*[^)]*request\.', 'get_object_or_404 with request data without ownership check'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for view functions that accept IDs
                    for i, line in enumerate(lines, 1):
                        # Check for function definitions that might accept IDs
                        if re.search(r'def\s+\w+\(request[^)]*id|def\s+\w+\(request[^)]*public_id', line):
                            func_start = i
                            func_end = min(len(lines), i + 150)
                            
                            has_id_param = 'id' in line or 'public_id' in line
                            has_ownership_check = False
                            has_user_filter = False
                            
                            # Check function body for ownership checks
                            for j in range(func_start, func_end):
                                if 'request.user' in lines[j] and ('owner' in lines[j] or 'created_by' in lines[j] or 'user' in lines[j]):
                                    has_ownership_check = True
                                if '.filter(' in lines[j] and 'request.user' in lines[j]:
                                    has_user_filter = True
                                if 'get_object_or_404' in lines[j] and 'request.user' in lines[j]:
                                    has_ownership_check = True
                            
                            if has_id_param and not has_ownership_check and not has_user_filter:
                                # Check if it's a public endpoint (GET only, no state changes)
                                is_public = False
                                for j in range(max(0, i-10), i):
                                    if '@require_http_methods' in lines[j] and 'GET' in lines[j] and 'POST' not in lines[j]:
                                        is_public = True
                                        break
                                
                                if not is_public:
                                    findings.append(SecurityFinding(
                                        severity='Critical',
                                        category='BOLA',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description="Object access by ID without ownership check - BOLA vulnerability",
                                        recommendation="Add ownership check: filter by request.user or verify object belongs to user before access"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_idor_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 15: Find IDOR (Insecure Direct Object Reference) vulnerabilities.
        
        Checks for:
        - Query parameters used to fetch objects without authorization
        - Predictable identifiers
        - Missing ownership validation
        """
        findings = []
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Look for query parameter usage
                        if re.search(r'request\.GET\.get\([^)]*id|request\.POST\.get\([^)]*id|request\.GET\.get\([^)]*user_id', line):
                            # Check if ownership is verified
                            func_start = max(0, i - 50)  # Look back for function start
                            func_end = min(len(lines), i + 100)
                            
                            has_ownership_check = False
                            
                            # Check surrounding code for ownership validation
                            for j in range(func_start, func_end):
                                if 'request.user' in lines[j] and ('owner' in lines[j] or 'created_by' in lines[j] or 'user' in lines[j]):
                                    has_ownership_check = True
                                if '.filter(' in lines[j] and 'request.user' in lines[j] and 'id' in line:
                                    has_ownership_check = True
                            
                            if not has_ownership_check:
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='IDOR',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Query parameter used to fetch object without ownership check - IDOR vulnerability",
                                    recommendation="Verify object ownership before access. Filter queryset by request.user"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_rate_limit_bypass_risks(self) -> List[SecurityFinding]:
        """
        UNIT 16: Find rate-limit bypass vulnerabilities.
        
        Checks for:
        - Rate limiting that trusts X-Forwarded-For
        - Single-identifier rate limiting
        - Missing persistent counters
        """
        findings = []
        
        # Check rate limiting implementation
        rate_limit_file = self.project_root / 'accounts' / 'rate_limiting.py'
        if rate_limit_file.exists():
            try:
                with open(rate_limit_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check if X-Forwarded-For is used without validation
                    for i, line in enumerate(lines, 1):
                        if 'X-Forwarded-For' in line or 'HTTP_X_FORWARDED_FOR' in line:
                            # Check if it's validated or sanitized
                            if 'REMOTE_ADDR' not in content or 'get_client_ip' not in content:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Rate-Limit Bypass',
                                    file_path=str(rate_limit_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Rate limiting may trust X-Forwarded-For header - can be spoofed",
                                    recommendation="Use REMOTE_ADDR or validate X-Forwarded-For against trusted proxies. Don't trust headers blindly"
                                ))
            except Exception:
                pass
        
        return findings
    
    def find_mass_assignment_risks(self) -> List[SecurityFinding]:
        """
        UNIT 17: Find mass assignment vulnerabilities.
        
        Checks for:
        - Direct model(**request.data)
        - Serializers without explicit fields
        - Writable sensitive fields
        """
        findings = []
        
        dangerous_patterns = [
            (r'Model\([^)]*\*\*request\.', 'Direct model instantiation with request data'),
            (r'Model\([^)]*\*\*data', 'Direct model instantiation with unvalidated data'),
            (r'\.objects\.create\([^)]*\*\*request\.', 'Model creation with request data'),
            (r'\.objects\.update\([^)]*\*\*request\.', 'Model update with request data'),
        ]
        
        sensitive_fields = [
            'is_superuser', 'is_staff', 'is_active', 'role', 'status',
            'owner', 'created_by', 'is_verified', 'is_approved',
            'permissions', 'groups', 'user_permissions'
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
                                    category='Mass Assignment',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description=f"Mass assignment risk: {description}",
                                    recommendation="Use explicit field whitelisting. Never use **request.data or **payload directly"
                                ))
                        
                        # Check for sensitive fields being set from request
                        for field in sensitive_fields:
                            if f'{field}=' in line and ('request.' in line or 'data.get' in line or 'payload' in line):
                                # Check if it's explicitly allowed or protected
                                if 'read_only' not in content and f'fields = ' not in content:
                                    findings.append(SecurityFinding(
                                        severity='High',
                                        category='Mass Assignment',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description=f"Sensitive field '{field}' may be settable from request",
                                        recommendation=f"Ensure '{field}' is read_only or explicitly protected from user input"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_state_manipulation_risks(self) -> List[SecurityFinding]:
        """
        UNIT 18: Find object state manipulation vulnerabilities.
        
        Checks for:
        - State transitions without validation
        - Missing authorization for state changes
        - Illegal state transitions
        """
        findings = []
        
        state_fields = ['status', 'state', 'visibility', 'is_active', 'is_approved', 'is_verified']
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Look for state field assignments
                        for field in state_fields:
                            if f'.{field} =' in line or f'[{field}]' in line:
                                # Check if state transition is validated
                                func_start = max(0, i - 100)
                                func_end = min(len(lines), i + 50)
                                
                                has_validation = False
                                has_authorization = False
                                
                                # Check for validation logic
                                for j in range(func_start, func_end):
                                    if 'validate' in lines[j].lower() or 'transition' in lines[j].lower() or 'allowed' in lines[j].lower():
                                        has_validation = True
                                    if 'request.user' in lines[j] and ('role' in lines[j] or 'permission' in lines[j] or 'admin' in lines[j]):
                                        has_authorization = True
                                
                                if not has_validation and not has_authorization:
                                    findings.append(SecurityFinding(
                                        severity='High',
                                        category='State Manipulation',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description=f"State field '{field}' updated without validation or authorization",
                                        recommendation="Validate state transitions. Ensure only allowed transitions are possible. Check user permissions"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_pagination_enumeration_risks(self) -> List[SecurityFinding]:
        """
        UNIT 19: Find pagination and enumeration vulnerabilities.
        
        Checks for:
        - Missing page size limits
        - Unrestricted enumeration
        - Excessive data exposure
        """
        findings = []
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for Paginator usage
                    for i, line in enumerate(lines, 1):
                        if 'Paginator' in line or 'paginate' in line.lower():
                            # Check for page size limits
                            func_start = max(0, i - 50)
                            func_end = min(len(lines), i + 50)
                            
                            has_size_limit = False
                            max_size = None
                            
                            # Check for size limits
                            for j in range(func_start, func_end):
                                if 'per_page' in lines[j] or 'page_size' in lines[j]:
                                    # Extract number
                                    numbers = re.findall(r'\d+', lines[j])
                                    if numbers:
                                        max_size = int(numbers[0])
                                        if max_size <= 100:  # Reasonable limit
                                            has_size_limit = True
                                if 'max' in lines[j].lower() and ('100' in lines[j] or '50' in lines[j] or '25' in lines[j]):
                                    has_size_limit = True
                            
                            if not has_size_limit:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Pagination Enumeration',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Pagination without size limits - vulnerable to enumeration",
                                    recommendation="Enforce maximum page size (e.g., 50-100 items per page). Prevent unlimited enumeration"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_verb_tampering_risks(self) -> List[SecurityFinding]:
        """
        UNIT 20: Find HTTP verb tampering vulnerabilities.
        
        Checks for:
        - Missing method restrictions
        - Verb confusion
        """
        findings = []
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for view functions that modify state
                    for i, line in enumerate(lines, 1):
                        if re.search(r'def\s+\w+\(request', line):
                            # Check if it's a state-changing operation
                            func_start = i
                            func_end = min(len(lines), i + 50)
                            
                            is_state_changing = False
                            has_method_restriction = False
                            
                            # Check decorators
                            for j in range(max(0, i-15), i):
                                if '@require_POST' in lines[j] or '@require_http_methods' in lines[j]:
                                    has_method_restriction = True
                            
                            # Check function body
                            for j in range(func_start, func_end):
                                if any(op in lines[j] for op in ['.save()', '.create(', '.update(', '.delete(', '.set(']):
                                    is_state_changing = True
                            
                            if is_state_changing and not has_method_restriction:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='HTTP Verb Tampering',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="State-changing view without HTTP method restriction",
                                    recommendation="Add @require_POST or @require_http_methods(['POST']) to prevent verb tampering"
                                ))
            except Exception:
                continue
        
        return findings
    
    def generate_test_report(self) -> str:
        """Generate comprehensive security test report."""
        report = []
        report.append("=" * 80)
        report.append("SECURITY TEST REPORT - API ABUSE & AUTHORIZATION (PART 3)")
        report.append("=" * 80)
        report.append("")
        
        # Run all tests
        bola_findings = self.find_bola_vulnerabilities()
        idor_findings = self.find_idor_vulnerabilities()
        rate_limit_bypass_findings = self.find_rate_limit_bypass_risks()
        mass_assignment_findings = self.find_mass_assignment_risks()
        state_manipulation_findings = self.find_state_manipulation_risks()
        pagination_findings = self.find_pagination_enumeration_risks()
        verb_tampering_findings = self.find_verb_tampering_risks()
        
        all_findings = (
            bola_findings + idor_findings + rate_limit_bypass_findings +
            mass_assignment_findings + state_manipulation_findings +
            pagination_findings + verb_tampering_findings
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
    Run all PART 3 security tests and return report and findings.
    
    Usage:
        report, findings = run_security_tests()
        print(report)
    """
    tester = APIAbuseSecurityTester(project_root)
    report = tester.generate_test_report()
    
    # Collect all findings
    all_findings = (
        tester.find_bola_vulnerabilities() +
        tester.find_idor_vulnerabilities() +
        tester.find_rate_limit_bypass_risks() +
        tester.find_mass_assignment_risks() +
        tester.find_state_manipulation_risks() +
        tester.find_pagination_enumeration_risks() +
        tester.find_verb_tampering_risks()
    )
    
    return report, all_findings


if __name__ == '__main__':
    # Run tests when executed directly
    report, findings = run_security_tests()
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent.parent / 'SECURITY_TEST_REPORT_PART3.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")




















