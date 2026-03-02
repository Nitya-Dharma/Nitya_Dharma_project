"""
Django management command to add multiple sample reviews for testing.

Usage:
    python manage.py add_multiple_sample_reviews
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reviews.services import ReviewService
from reviews.models import Review
from reviews.models_advanced import ReviewHelpfulVote

User = get_user_model()


class Command(BaseCommand):
    help = 'Add multiple sample reviews with different ratings and features for testing'

    def handle(self, *args, **options):
        # Get or create test users
        test_users = []
        for i in range(1, 6):
            email = f'testuser{i}@example.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Test',
                    'last_name': f'User{i}',
                    'role': 'user',
                    'status': 'active',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            test_users.append(user)

        # Get first active pandit
        pandit = User.objects.filter(role='pandit', status='active', is_active=True).first()
        if not pandit:
            self.stdout.write(self.style.ERROR('No active pandit found. Please create a pandit first.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Using pandit: {pandit.email}'))
        self.stdout.write(self.style.SUCCESS(f'Creating {len(test_users)} sample reviews...\n'))

        # Sample reviews data
        reviews_data = [
            {
                'rating': 5,
                'title': 'Outstanding Service - Exceeded Expectations!',
                'text': 'Absolutely fantastic experience! The pandit was extremely knowledgeable, punctual, and conducted the pooja with great devotion. Every ritual was explained clearly, and the spiritual atmosphere was truly uplifting. Highly recommend their services to anyone looking for authentic and meaningful ceremonies.',
                'verified': True,
            },
            {
                'rating': 5,
                'title': 'Excellent Pandit - Very Professional',
                'text': 'Great service from start to finish. The pandit arrived on time, was well-prepared, and conducted the ceremony beautifully. The attention to detail and traditional authenticity was impressive. Would definitely book again for future ceremonies.',
                'verified': False,
            },
            {
                'rating': 4,
                'title': 'Good Service Overall',
                'text': 'The pandit was professional and the ceremony went well. There were minor delays, but overall it was a positive experience. The rituals were conducted properly and the pandit was helpful in explaining the significance of each step.',
                'verified': False,
            },
            {
                'rating': 4,
                'title': 'Satisfactory Experience',
                'text': 'Decent service with good knowledge of rituals. The ceremony was completed successfully, though I felt some aspects could have been explained better. Overall, would consider using their services again.',
                'verified': False,
            },
            {
                'rating': 3,
                'title': 'Average Service',
                'text': 'The service was okay, but there were some areas that could be improved. The pandit was knowledgeable but seemed rushed at times. The ceremony was completed, but I expected more attention to detail and better communication.',
                'verified': False,
            },
        ]

        created_count = 0
        updated_count = 0

        for i, (user, review_data) in enumerate(zip(test_users, reviews_data)):
            try:
                # Check if review exists
                existing_review = Review.objects.filter(user=user, pandit=pandit).first()
                
                if existing_review:
                    # Update existing review
                    existing_review.rating = review_data['rating']
                    existing_review.title = review_data['title']
                    existing_review.review_text = review_data['text']
                    existing_review.is_verified = review_data['verified']
                    existing_review.save()
                    updated_count += 1
                    review = existing_review
                    self.stdout.write(f'  Updated review for {user.email} (Rating: {review_data["rating"]}/5)')
                else:
                    # Create new review
                    review = ReviewService.create_review(
                        reviewer=user,
                        pandit_id=pandit.id,
                        rating=review_data['rating'],
                        review_text=review_data['text'],
                        title=review_data['title'],
                        booking_intent_id=None
                    )
                    
                    if review_data['verified']:
                        review.is_verified = True
                        review.save(update_fields=['is_verified'])
                    
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created review for {user.email} (Rating: {review_data["rating"]}/5)'))

                # Add helpful votes (randomly)
                if i < 3:  # First 3 reviews get helpful votes
                    other_users = [u for u in test_users if u.id != user.id][:2]
                    for voter in other_users:
                        ReviewHelpfulVote.objects.get_or_create(
                            review=review,
                            user=voter
                        )
                    review.refresh_from_db()
                    if review.helpful_count > 0:
                        self.stdout.write(f'    - {review.helpful_count} helpful vote(s)')

            except ValueError as e:
                self.stdout.write(self.style.ERROR(f'  Error for {user.email}: {str(e)}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Unexpected error for {user.email}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nCompleted!\n'
            f'  Created: {created_count} reviews\n'
            f'  Updated: {updated_count} reviews\n'
            f'  Total: {created_count + updated_count} reviews\n'
        ))













