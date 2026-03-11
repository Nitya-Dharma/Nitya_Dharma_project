"""Test email delivery with detailed diagnostics"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
import django
django.setup()

from django.conf import settings
from django.core.mail import send_mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

print("=" * 80)
print("COMPREHENSIVE EMAIL DELIVERY TEST")
print("=" * 80)
print()

# 1. Configuration Check
print("1. EMAIL CONFIGURATION:")
print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print()

# 2. FROM Address Match Check
print("2. FROM ADDRESS VERIFICATION:")
if settings.EMAIL_HOST_USER == settings.DEFAULT_FROM_EMAIL:
    print(f"   [OK] FROM address matches EMAIL_HOST_USER: {settings.DEFAULT_FROM_EMAIL}")
else:
    print(f"   [ERROR] FROM address MISMATCH!")
    print(f"     EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"     DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"     Gmail will silently drop emails!")
    exit(1)
print()

# 3. SMTP Connection Test
print("3. SMTP CONNECTION TEST:")
try:
    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    server.starttls()
    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    print("   [OK] SMTP connection successful")
    print("   [OK] SMTP authentication successful")
    server.quit()
except Exception as e:
    print(f"   [ERROR] SMTP connection failed: {e}")
    exit(1)
print()

# 4. Test Email Send
print("4. TEST EMAIL SEND:")
recipient = input("Enter recipient email (or press Enter to use EMAIL_HOST_USER): ").strip()
if not recipient:
    recipient = settings.EMAIL_HOST_USER

print(f"   Sending test email to: {recipient}")
print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
print()

try:
    result = send_mail(
        subject='Test Email - Nitya Dharma Email Verification System',
        message=f"""
This is a test email from the Nitya Dharma email verification system.

If you receive this email, it means:
✓ SMTP configuration is correct
✓ FROM address matches authenticated account
✓ Email delivery is working

Configuration:
- FROM: {settings.DEFAULT_FROM_EMAIL}
- SMTP Host: {settings.EMAIL_HOST}
- SMTP Port: {settings.EMAIL_PORT}
- TLS: {settings.EMAIL_USE_TLS}

Please check:
1. Inbox folder
2. Spam folder
3. Promotions tab (if using Gmail tabs)
4. All Mail folder

If you don't see this email in any folder, it may be:
- Gmail's automatic spam filtering (not user-configured)
- Email delivery delay (wait 2-3 minutes)
- Network/firewall blocking SMTP

Best regards,
Nitya Dharma Email System
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
    
    print("=" * 80)
    print("EMAIL SEND RESULT:")
    print("=" * 80)
    print(f"   Result: {result} (1 = success, 0 = failure)")
    print()
    
    if result == 1:
        print("   [OK] Email sent successfully via SMTP")
        print("   [OK] SMTP server accepted the email")
        print()
        print("   NEXT STEPS:")
        print("   1. Wait 2-3 minutes for email delivery")
        print("   2. Check inbox: " + recipient)
        print("   3. Check spam folder")
        print("   4. Check Promotions tab (if using Gmail tabs)")
        print("   5. Check All Mail folder")
        print()
        print("   GMAIL TROUBLESHOOTING:")
        print("   - Gmail may automatically filter emails to spam (not user filters)")
        print("   - Check 'All Mail' folder - emails may be there but not in inbox")
        print("   - Gmail may delay delivery by 2-3 minutes")
        print("   - Try searching for: 'from:YOUR_SENDER_EMAIL' in Gmail (use the value of EMAIL_HOST_USER)")
    else:
        print("   [ERROR] Email send returned 0 (failure)")
        print("   Check SMTP credentials and network connection")
    
except Exception as e:
    print("=" * 80)
    print("EMAIL SEND FAILED:")
    print("=" * 80)
    print(f"   Error Type: {type(e).__name__}")
    print(f"   Error Message: {str(e)}")
    print()
    import traceback
    traceback.print_exc()
    exit(1)

print("=" * 80)

