"""
Security Tests: Session, Auth & State Attacks (PART 2)

UNIT 7-13: CSRF, Clickjacking, Session Fixation, Auth Logic Flaws,
Credential Stuffing, Password Reset Abuse, Logout Failures

This module provides test utilities and code review functions for authentication
and session management vulnerabilities.
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
    category: str  # 'CSRF', 'Clickjacking', etc.
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str


class SessionAuthSecurityTester:
    """Security testing utilities for session and authentication attacks."""
    
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
    
    def find_csrf_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 7: Find CSRF vulnerabilities.
        
        Searches for:
        - POST/PUT/PATCH/DELETE endpoints without CSRF protection
        - @csrf_exempt decorators
        - Missing CSRF token validation
        """
        findings = []
        
        dangerous_patterns = [
            (r'@csrf_exempt', 'CSRF protection disabled'),
            (r'csrf_exempt\s*\(', 'CSRF protection disabled'),
        ]
        
        # Search Python files
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check for @csrf_exempt
                    for i, line in enumerate(lines, 1):
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line):
                                # Check if it's a state-changing endpoint
                                # Look for POST, PUT, PATCH, DELETE in nearby lines
                                is_state_changing = False
                                for j in range(max(0, i-10), min(len(lines), i+10)):
                                    if re.search(r'@require_POST|@require_http_methods|POST|PUT|PATCH|DELETE', lines[j], re.IGNORECASE):
                                        is_state_changing = True
                                        break
                                
                                if is_state_changing:
                                    findings.append(SecurityFinding(
                                        severity='Critical',
                                        category='CSRF',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description=f"CSRF protection disabled: {description}",
                                        recommendation="Remove @csrf_exempt or add CSRF token validation. Use @csrf_protect for state-changing endpoints"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_clickjacking_vulnerabilities(self) -> List[SecurityFinding]:
        """
        UNIT 8: Find clickjacking vulnerabilities.
        
        Checks for:
        - Missing X-Frame-Options header
        - Missing CSP frame-ancestors
        - Inconsistent clickjacking protection
        """
        findings = []
        
        # Check settings.py for middleware
        settings_file = self.project_root / 'nityadharma' / 'settings.py'
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for SecurityMiddleware (provides X-Frame-Options)
                    if 'SecurityMiddleware' not in content:
                        findings.append(SecurityFinding(
                            severity='High',
                            category='Clickjacking',
                            file_path=str(settings_file.relative_to(self.project_root)),
                            line_number=1,
                            code_snippet='MIDDLEWARE = [...]',
                            description="SecurityMiddleware not found - X-Frame-Options may be missing",
                            recommendation="Add 'django.middleware.security.SecurityMiddleware' to MIDDLEWARE. It provides X-Frame-Options: DENY by default"
                        ))
                    
                    # Check for custom X-Frame-Options setting
                    if 'X_FRAME_OPTIONS' in content:
                        # Check if it's set to DENY or SAMEORIGIN
                        if re.search(r"X_FRAME_OPTIONS\s*=\s*['\"]ALLOW", content, re.IGNORECASE):
                            findings.append(SecurityFinding(
                                severity='Critical',
                                category='Clickjacking',
                                file_path=str(settings_file.relative_to(self.project_root)),
                                line_number=1,
                                code_snippet='X_FRAME_OPTIONS = ...',
                                description="X_FRAME_OPTIONS set to ALLOW - clickjacking protection disabled",
                                recommendation="Set X_FRAME_OPTIONS = 'DENY' or use CSP frame-ancestors 'none'"
                            ))
            except Exception:
                pass
        
        # Check for views that might need exceptions (should be rare)
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        if 'X_FRAME_OPTIONS' in line and 'ALLOW' in line.upper():
                            findings.append(SecurityFinding(
                                severity='High',
                                category='Clickjacking',
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=i,
                                code_snippet=line.strip(),
                                description="X_FRAME_OPTIONS set to ALLOW in view",
                                recommendation="Review if clickjacking exception is necessary. Use DENY or SAMEORIGIN instead"
                            ))
            except Exception:
                continue
        
        return findings
    
    def find_session_fixation_risks(self) -> List[SecurityFinding]:
        """
        UNIT 9: Find session fixation vulnerabilities.
        
        Checks for:
        - Session not regenerated after login
        - Session reuse patterns
        """
        findings = []
        
        # Check authentication views
        auth_files = [
            self.project_root / 'accounts' / 'views.py',
        ]
        
        for auth_file in auth_files:
            if not auth_file.exists():
                continue
            
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for login functions
                    login_functions = []
                    for i, line in enumerate(lines, 1):
                        if re.search(r'def\s+\w*login\w*', line, re.IGNORECASE):
                            login_functions.append(i)
                    
                    # Check each login function for session regeneration
                    for func_line in login_functions:
                        # Look for login() call
                        has_login_call = False
                        has_session_regenerate = False
                        
                        # Check next 50 lines for login() and session regeneration
                        for i in range(func_line, min(len(lines), func_line + 50)):
                            if 'login(' in lines[i] or 'authenticate(' in lines[i]:
                                has_login_call = True
                            if 'request.session.cycle_key()' in lines[i] or 'request.session.flush()' in lines[i]:
                                has_session_regenerate = True
                            if 'from django.contrib.auth import login' in lines[i]:
                                has_login_call = True
                        
                        if has_login_call and not has_session_regenerate:
                            findings.append(SecurityFinding(
                                severity='Critical',
                                category='Session Fixation',
                                file_path=str(auth_file.relative_to(self.project_root)),
                                line_number=func_line,
                                code_snippet=lines[func_line-1].strip(),
                                description="Login function may not regenerate session - session fixation risk",
                                recommendation="Call request.session.cycle_key() after successful authentication to regenerate session ID"
                            ))
            except Exception:
                continue
        
        return findings
    
    def find_auth_logic_flaws(self) -> List[SecurityFinding]:
        """
        UNIT 10: Find authentication logic flaws.
        
        Checks for:
        - Missing @login_required decorators
        - Bypass patterns
        - Partial auth access
        """
        findings = []
        
        # Patterns that might indicate auth bypass
        dangerous_patterns = [
            (r'if\s+not\s+request\.user\.is_authenticated.*return\s+redirect', 'Auth check with redirect - may allow partial access'),
            (r'if\s+request\.user\.is_authenticated\s*:\s*pass', 'Empty auth check'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            file_str = str(py_file)
            if any(skip in file_str for skip in ['test', 'migration', 'venv', 'site-packages', '__pycache__', '.pyc']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check for views that access user data but don't have @login_required
                    for i, line in enumerate(lines, 1):
                        # Look for view functions
                        if re.search(r'def\s+\w+\(request', line):
                            # Check if function accesses user data
                            func_start = i
                            func_end = min(len(lines), i + 100)
                            
                            accesses_user = False
                            has_login_required = False
                            
                            # Check decorators before function
                            for j in range(max(0, i-10), i):
                                if '@login_required' in lines[j] or '@require_auth' in lines[j]:
                                    has_login_required = True
                            
                            # Check function body
                            for j in range(func_start, func_end):
                                if 'request.user' in lines[j] or 'user.is_authenticated' in lines[j]:
                                    accesses_user = True
                                if 'request.user.is_authenticated' in lines[j] and 'if not' in lines[j]:
                                    # Manual check - may be okay but worth reviewing
                                    pass
                            
                            if accesses_user and not has_login_required:
                                # Check if it's a public view (GET only, no state changes)
                                is_public = False
                                for j in range(max(0, i-10), i):
                                    if '@require_http_methods' in lines[j] and 'GET' in lines[j] and 'POST' not in lines[j]:
                                        is_public = True
                                        break
                                
                                if not is_public:
                                    findings.append(SecurityFinding(
                                        severity='High',
                                        category='Authentication Logic Flaw',
                                        file_path=str(py_file.relative_to(self.project_root)),
                                        line_number=i,
                                        code_snippet=line.strip(),
                                        description="View accesses user data without @login_required decorator",
                                        recommendation="Add @login_required decorator or verify view is intentionally public"
                                    ))
            except Exception:
                continue
        
        return findings
    
    def find_brute_force_risks(self) -> List[SecurityFinding]:
        """
        UNIT 11: Find credential stuffing and brute force vulnerabilities.
        
        Checks for:
        - Missing rate limiting on login
        - Detailed error messages
        - No account lockout
        """
        findings = []
        
        # Check login views
        auth_files = [
            self.project_root / 'accounts' / 'views.py',
        ]
        
        for auth_file in auth_files:
            if not auth_file.exists():
                continue
            
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for login functions
                    for i, line in enumerate(lines, 1):
                        if re.search(r'def\s+\w*login\w*', line, re.IGNORECASE):
                            # Check for rate limiting
                            has_rate_limit = False
                            has_detailed_error = False
                            
                            # Check next 100 lines
                            for j in range(i, min(len(lines), i + 100)):
                                if 'rate_limit' in lines[j] or 'throttle' in lines[j] or 'RateLimiter' in lines[j]:
                                    has_rate_limit = True
                                if 'Invalid password' in lines[j] or 'User not found' in lines[j] or 'does not exist' in lines[j]:
                                    has_detailed_error = True
                            
                            if not has_rate_limit:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Brute Force',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Login endpoint may lack rate limiting - vulnerable to brute force",
                                    recommendation="Add rate limiting using django-ratelimit or similar. Limit login attempts per IP/user"
                                ))
                            
                            if has_detailed_error:
                                findings.append(SecurityFinding(
                                    severity='Medium',
                                    category='Brute Force',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Login endpoint provides detailed error messages - enables user enumeration",
                                    recommendation="Use generic error messages like 'Invalid credentials' instead of specific errors"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_password_reset_abuse(self) -> List[SecurityFinding]:
        """
        UNIT 12: Find password reset flow vulnerabilities.
        
        Checks for:
        - Predictable tokens
        - No expiry
        - User enumeration
        """
        findings = []
        
        # Check password reset views
        auth_files = [
            self.project_root / 'accounts' / 'views.py',
        ]
        
        for auth_file in auth_files:
            if not auth_file.exists():
                continue
            
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for password reset functions
                    for i, line in enumerate(lines, 1):
                        if re.search(r'def\s+\w*reset\w*', line, re.IGNORECASE) or re.search(r'def\s+\w*password\w*reset\w*', line, re.IGNORECASE):
                            # Check for token generation
                            has_secure_token = False
                            has_expiry = False
                            has_user_enum = False
                            
                            # Check next 100 lines
                            for j in range(i, min(len(lines), i + 100)):
                                if 'secrets.token_urlsafe' in lines[j] or 'default_token_generator' in lines[j] or 'PasswordResetTokenGenerator' in lines[j]:
                                    has_secure_token = True
                                if 'expires' in lines[j] or 'expiry' in lines[j] or 'timedelta' in lines[j]:
                                    has_expiry = True
                                if 'User not found' in lines[j] or 'does not exist' in lines[j]:
                                    has_user_enum = True
                            
                            if not has_secure_token:
                                findings.append(SecurityFinding(
                                    severity='Critical',
                                    category='Password Reset Abuse',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Password reset may use predictable tokens",
                                    recommendation="Use Django's default_token_generator or secrets.token_urlsafe() for secure random tokens"
                                ))
                            
                            if not has_expiry:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Password Reset Abuse',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Password reset tokens may not expire",
                                    recommendation="Set token expiry (typically 24-48 hours). Use timezone.now() + timedelta(hours=24)"
                                ))
                            
                            if has_user_enum:
                                findings.append(SecurityFinding(
                                    severity='Medium',
                                    category='Password Reset Abuse',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Password reset reveals user existence - enables enumeration",
                                    recommendation="Return same success message regardless of user existence to prevent enumeration"
                                ))
            except Exception:
                continue
        
        return findings
    
    def find_logout_failures(self) -> List[SecurityFinding]:
        """
        UNIT 13: Find logout and session invalidation failures.
        
        Checks for:
        - Session not invalidated on logout
        - Cookies not cleared
        """
        findings = []
        
        # Check logout views
        auth_files = [
            self.project_root / 'accounts' / 'views.py',
        ]
        
        for auth_file in auth_files:
            if not auth_file.exists():
                continue
            
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for logout functions
                    for i, line in enumerate(lines, 1):
                        if re.search(r'def\s+\w*logout\w*', line, re.IGNORECASE):
                            # Check for session invalidation
                            has_logout_call = False
                            has_session_flush = False
                            
                            # Check next 30 lines
                            for j in range(i, min(len(lines), i + 30)):
                                if 'logout(' in lines[j] or 'from django.contrib.auth import logout' in lines[j]:
                                    has_logout_call = True
                                if 'request.session.flush()' in lines[j] or 'request.session.clear()' in lines[j]:
                                    has_session_flush = True
                            
                            if has_logout_call and not has_session_flush:
                                findings.append(SecurityFinding(
                                    severity='High',
                                    category='Logout Failure',
                                    file_path=str(auth_file.relative_to(self.project_root)),
                                    line_number=i,
                                    code_snippet=line.strip(),
                                    description="Logout may not invalidate session - session persists after logout",
                                    recommendation="Call request.session.flush() after logout() to invalidate session server-side"
                                ))
            except Exception:
                continue
        
        return findings
    
    def generate_test_report(self) -> str:
        """Generate comprehensive security test report."""
        report = []
        report.append("=" * 80)
        report.append("SECURITY TEST REPORT - SESSION & AUTH ATTACKS (PART 2)")
        report.append("=" * 80)
        report.append("")
        
        # Run all tests
        csrf_findings = self.find_csrf_vulnerabilities()
        clickjacking_findings = self.find_clickjacking_vulnerabilities()
        session_fixation_findings = self.find_session_fixation_risks()
        auth_logic_findings = self.find_auth_logic_flaws()
        brute_force_findings = self.find_brute_force_risks()
        password_reset_findings = self.find_password_reset_abuse()
        logout_findings = self.find_logout_failures()
        
        all_findings = (
            csrf_findings + clickjacking_findings + session_fixation_findings +
            auth_logic_findings + brute_force_findings + password_reset_findings +
            logout_findings
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
    Run all PART 2 security tests and return report and findings.
    
    Usage:
        report, findings = run_security_tests()
        print(report)
    """
    tester = SessionAuthSecurityTester(project_root)
    report = tester.generate_test_report()
    
    # Collect all findings
    all_findings = (
        tester.find_csrf_vulnerabilities() +
        tester.find_clickjacking_vulnerabilities() +
        tester.find_session_fixation_risks() +
        tester.find_auth_logic_flaws() +
        tester.find_brute_force_risks() +
        tester.find_password_reset_abuse() +
        tester.find_logout_failures()
    )
    
    return report, all_findings


if __name__ == '__main__':
    # Run tests when executed directly
    report, findings = run_security_tests()
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent.parent / 'SECURITY_TEST_REPORT_PART2.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")




















