"""
Django management command to add a sample review for testing.

Usage:
    python manage.py add_sample_review
    python manage.py add_sample_review --pandit-email pandit@example.com
    python manage.py add_sample_review --user-email user@example.com --pandit-email pandit@example.com
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reviews.services import ReviewService
from reviews.models import Review

User = get_user_model()


class Command(BaseCommand):
    help = 'Add a sample review for testing the advanced review system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user who will write the review (default: creates test user)',
        )
        parser.add_argument(
            '--pandit-email',
            type=str,
            help='Email of the pandit to review (default: uses first active pandit)',
        )
        parser.add_argument(
            '--rating',
            type=int,
            default=5,
            choices=[1, 2, 3, 4, 5],
            help='Rating for the review (1-5, default: 5)',
        )
        parser.add_argument(
            '--verified',
            action='store_true',
            help='Mark the review as verified',
        )

    def handle(self, *args, **options):
        user_email = options.get('user_email')
        pandit_email = options.get('pandit_email')
        rating = options.get('rating', 5)
        verified = options.get('verified', False)

        # Get or create reviewer (user)
        if user_email:
            try:
                reviewer = User.objects.get(email=user_email, role='user', status='active')
                self.stdout.write(self.style.SUCCESS(f'Using existing user: {user_email}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with email {user_email} not found or not eligible'))
                return
        else:
            # Create test user if doesn't exist
            reviewer, created = User.objects.get_or_create(
                email='testuser@example.com',
                defaults={
                    'first_name': 'Test',
                    'last_name': 'User',
                    'role': 'user',
                    'status': 'active',
                    'is_active': True,
                }
            )
            if created:
                reviewer.set_password('testpass123')
                reviewer.save()
                self.stdout.write(self.style.SUCCESS('Created test user: testuser@example.com'))
            else:
                self.stdout.write(self.style.SUCCESS('Using existing test user: testuser@example.com'))

        # Get pandit
        if pandit_email:
            try:
                pandit = User.objects.get(email=pandit_email, role='pandit', status='active', is_active=True)
                self.stdout.write(self.style.SUCCESS(f'Using pandit: {pandit_email}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Pandit with email {pandit_email} not found or not eligible'))
                return
        else:
            # Get first active pandit
            pandit = User.objects.filter(role='pandit', status='active', is_active=True).first()
            if not pandit:
                self.stdout.write(self.style.ERROR('No active pandit found. Please create a pandit first or use --pandit-email'))
                return
            self.stdout.write(self.style.SUCCESS(f'Using first active pandit: {pandit.email}'))

        # Check if review already exists
        existing_review = Review.objects.filter(user=reviewer, pandit=pandit).first()
        if existing_review:
            self.stdout.write(self.style.WARNING(f'Review already exists (ID: {existing_review.id}). Updating it...'))
            existing_review.rating = rating
            existing_review.title = 'Excellent Service - Highly Recommended!'
            existing_review.review_text = (
                'I had a wonderful experience with this pandit. The pooja was conducted with great devotion and attention to detail. '
                'The pandit was very knowledgeable, punctual, and explained everything clearly. The entire ceremony was conducted '
                'with traditional authenticity while being accessible and meaningful. I would definitely recommend their services to others. '
                'The positive energy and spiritual guidance made it a truly memorable experience.'
            )
            existing_review.is_verified = verified
            existing_review.save()
            self.stdout.write(self.style.SUCCESS(f'Updated review ID: {existing_review.id}'))
            return

        # Sample review texts based on rating
        review_texts = {
            5: (
                'I had a wonderful experience with this pandit. The pooja was conducted with great devotion and attention to detail. '
                'The pandit was very knowledgeable, punctual, and explained everything clearly. The entire ceremony was conducted '
                'with traditional authenticity while being accessible and meaningful. I would definitely recommend their services to others. '
                'The positive energy and spiritual guidance made it a truly memorable experience.'
            ),
            4: (
                'Good service overall. The pandit was professional and the ceremony was well-organized. '
                'There were a few minor delays, but the overall experience was positive. Would consider using their services again.'
            ),
            3: (
                'Average experience. The pandit was okay, but there were some areas that could be improved. '
                'The ceremony was completed, but I expected more attention to detail and explanation of the rituals.'
            ),
            2: (
                'Below expectations. The service was not as professional as I hoped. There were some issues with timing and communication. '
                'The ceremony was completed, but I would not recommend this pandit.'
            ),
            1: (
                'Very disappointed with the service. Multiple issues occurred during the ceremony. '
                'Poor communication and lack of professionalism. Would not recommend.'
            ),
        }

        review_text = review_texts.get(rating, review_texts[5])
        title = 'Excellent Service - Highly Recommended!' if rating >= 4 else 'Review'

        try:
            # Create review using ReviewService
            review = ReviewService.create_review(
                reviewer=reviewer,
                pandit_id=pandit.id,
                rating=rating,
                review_text=review_text,
                title=title,
                booking_intent_id=None
            )

            # Mark as verified if requested
            if verified:
                review.is_verified = True
                review.save(update_fields=['is_verified'])

            self.stdout.write(self.style.SUCCESS(
                f'\nSample review created successfully!\n'
                f'   Review ID: {review.id}\n'
                f'   Reviewer: {reviewer.email}\n'
                f'   Pandit: {pandit.email}\n'
                f'   Rating: {rating}/5\n'
                f'   Verified: {review.is_verified}\n'
                f'   Public ID: {review.public_id}\n'
            ))

            # Add some helpful votes for testing
            from reviews.models_advanced import ReviewHelpfulVote
            from accounts.models import User as UserModel
            
            # Create a few test helpful votes
            test_users = UserModel.objects.filter(role='user', status='active', is_active=True).exclude(id=reviewer.id)[:3]
            for test_user in test_users:
                ReviewHelpfulVote.objects.get_or_create(
                    review=review,
                    user=test_user
                )
            
            review.refresh_from_db()
            if review.helpful_count > 0:
                self.stdout.write(self.style.SUCCESS(f'   Helpful votes: {review.helpful_count}'))

        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'Error creating review: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {str(e)}'))
            import traceback
            traceback.print_exc()

