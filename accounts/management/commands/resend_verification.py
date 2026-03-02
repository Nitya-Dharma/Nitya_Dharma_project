"""
Django management command to resend email verification for Pandit users.

Usage:
    python manage.py resend_verification <email>
    
Example:
    python manage.py resend_verification kabdeshriya2005@gmail.com
"""

from django.core.management.base import BaseCommand, CommandError
from accounts.models import User
from accounts.services import (
    resend_verification_email,
    VerificationAlreadyCompleted,
    CooldownNotElapsed
)


class Command(BaseCommand):
    help = 'Resend email verification for a Pandit user'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the Pandit user to resend verification for'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force resend even if user is already verified (use with caution)'
        )

    def handle(self, *args, **options):
        email = options['email']
        force = options.get('force', False)

        try:
            # Find user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f'User with email "{email}" does not exist.')

            # Check if user is Pandit
            if user.role != 'pandit':
                raise CommandError(
                    f'User "{email}" is not a Pandit. Email verification resend is only available for Pandit accounts.'
                )

            # Check verification status
            if user.email_verified and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'User "{email}" is already verified. Use --force to resend anyway.'
                    )
                )
                return

            # Resend verification email
            try:
                token = resend_verification_email(user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully resent verification email to {email}'
                    )
                )
                self.stdout.write(f'Token ID: {token.public_id}')
                self.stdout.write(f'Token expires at: {token.expires_at}')
                self.stdout.write(
                    self.style.WARNING(
                        'Please check inbox and spam folder for the verification email.'
                    )
                )
            except VerificationAlreadyCompleted:
                raise CommandError(
                    f'User "{email}" is already verified. Cannot resend verification email.'
                )
            except CooldownNotElapsed as e:
                raise CommandError(str(e))
            except Exception as e:
                raise CommandError(f'Failed to resend verification email: {str(e)}')

        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f'Unexpected error: {str(e)}')












