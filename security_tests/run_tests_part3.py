"""
Security Testing Runner - PART 3

Execute this script to run PART 3 security tests (API Abuse, BOLA/IDOR, etc.).
"""

import sys
import io
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from security_tests.test_api_abuse_attacks import run_security_tests


def main():
    """Run security tests and display results."""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("Running Security Tests - API Abuse & Authorization (PART 3)...")
    print("=" * 80)
    print()
    
    report, findings = run_security_tests()
    
    try:
        print(report)
    except UnicodeEncodeError:
        # Fallback: print ASCII-safe version
        print(report.encode('ascii', 'replace').decode('ascii'))
    
    # Save report
    report_file = project_root / 'SECURITY_TEST_REPORT_PART3.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[OK] Report saved to: {report_file}")
    print(f"\n[INFO] Total Findings: {len(findings)}")
    
    # Exit with error code if critical findings
    critical_count = len([f for f in findings if f.severity == 'Critical'])
    if critical_count > 0:
        print(f"\n[WARNING] {critical_count} Critical findings detected!")
        sys.exit(1)
    else:
        print("\n[OK] No critical findings detected.")
        sys.exit(0)


if __name__ == '__main__':
    main()




















