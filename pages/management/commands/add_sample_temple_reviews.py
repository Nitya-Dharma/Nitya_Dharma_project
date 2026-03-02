"""
Django management command to add sample temple reviews for testing.

Usage:
    python manage.py add_sample_temple_reviews
    python manage.py add_sample_temple_reviews --page-id <id>
    python manage.py add_sample_temple_reviews --page-public-id <public_id>
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pages.models import Page, PageReview
from pages.models_page_review_advanced import PageReviewHelpfulVote

User = get_user_model()


class Command(BaseCommand):
    help = 'Add sample temple reviews for testing the advanced review system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--page-id',
            type=int,
            help='ID of the page to add reviews to',
        )
        parser.add_argument(
            '--page-public-id',
            type=str,
            help='Public ID of the page to add reviews to',
        )

    def handle(self, *args, **options):
        page_id = options.get('page_id')
        page_public_id = options.get('page_public_id')
        
        # Get page
        if page_id:
            try:
                page = Page.objects.get(id=page_id, page_type='TEMPLE')
            except Page.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Page with ID {page_id} not found or not a temple'))
                return
        elif page_public_id:
            from core.public_id import resolve_public_id
            page = resolve_public_id(Page, page_public_id)
            if not page or page.page_type != 'TEMPLE':
                self.stdout.write(self.style.ERROR(f'Page with public_id {page_public_id} not found or not a temple'))
                return
        else:
            # Get first temple page
            page = Page.objects.filter(page_type='TEMPLE', status='ACTIVE').first()
            if not page:
                self.stdout.write(self.style.ERROR('No active temple pages found. Please create a temple page first or use --page-id'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Using temple page: {page.title} (ID: {page.id})'))
        
        # Get or create test users (all roles can review)
        test_users = []
        for i in range(1, 6):
            email = f'templetestuser{i}@example.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Temple',
                    'last_name': f'Reviewer{i}',
                    'role': 'user',  # All roles can review temples
                    'status': 'active',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            test_users.append(user)
        
        # Also add a pandit and admin as reviewers (all roles can review)
        pandit_user, _ = User.objects.get_or_create(
            email='templetestpandit@example.com',
            defaults={
                'first_name': 'Temple',
                'last_name': 'Pandit',
                'role': 'pandit',
                'status': 'active',
                'is_active': True,
            }
        )
        if _:
            pandit_user.set_password('testpass123')
            pandit_user.save()
        test_users.append(pandit_user)
        
        admin_user, _ = User.objects.get_or_create(
            email='templetestadmin@example.com',
            defaults={
                'first_name': 'Temple',
                'last_name': 'Admin',
                'role': 'admin',
                'status': 'active',
                'is_active': True,
            }
        )
        if _:
            admin_user.set_password('testpass123')
            admin_user.save()
        test_users.append(admin_user)
        
        self.stdout.write(self.style.SUCCESS(f'Creating {len(test_users)} sample reviews...\n'))
        
        # Sample reviews data
        reviews_data = [
            {
                'rating': 5,
                'text': 'Absolutely beautiful temple! The architecture is stunning and the spiritual atmosphere is truly peaceful. The priests are very knowledgeable and the ceremonies are conducted with great devotion. Highly recommend visiting this temple for a meaningful spiritual experience.',
                'verified': True,
            },
            {
                'rating': 5,
                'text': 'Wonderful temple with rich history and beautiful architecture. The staff is very helpful and the temple maintains excellent cleanliness. The daily poojas are conducted with great devotion. A must-visit for anyone seeking spiritual peace.',
                'verified': False,
            },
            {
                'rating': 4,
                'text': 'Great temple with good facilities. The location is convenient and the temple is well-maintained. The ceremonies are conducted properly. Would visit again for special occasions.',
                'verified': False,
            },
            {
                'rating': 4,
                'text': 'Nice temple with traditional architecture. The atmosphere is peaceful and the priests are helpful. The temple could benefit from better parking facilities, but overall a good experience.',
                'verified': False,
            },
            {
                'rating': 5,
                'text': 'Exceptional temple experience! The spiritual energy here is incredible. The temple management does an excellent job maintaining the premises. The festivals are celebrated with great enthusiasm. Highly recommended!',
                'verified': True,
            },
            {
                'rating': 4,
                'text': 'Good temple with traditional values. The architecture is impressive and the ceremonies are well-organized. The temple community is welcoming. A peaceful place for prayer and meditation.',
                'verified': False,
            },
            {
                'rating': 3,
                'text': 'Decent temple. The facilities are okay but could be improved. The ceremonies are conducted properly. The location is accessible but parking can be challenging during festivals.',
                'verified': False,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for i, (user, review_data) in enumerate(zip(test_users[:len(reviews_data)], reviews_data)):
            try:
                # Check if review exists
                existing_review = PageReview.objects.filter(page=page, user=user).first()
                
                if existing_review:
                    # Update existing review
                    existing_review.rating = review_data['rating']
                    existing_review.review_text = review_data['text']
                    existing_review.is_verified = review_data['verified']
                    existing_review.is_hidden = False
                    existing_review.visibility_state = PageReview.VISIBLE
                    existing_review.save()
                    updated_count += 1
                    review = existing_review
                    self.stdout.write(f'  Updated review for {user.email} (Rating: {review_data["rating"]}/5, Role: {user.role})')
                else:
                    # Create new review
                    review = PageReview.objects.create(
                        page=page,
                        user=user,
                        rating=review_data['rating'],
                        review_text=review_data['text'],
                        visibility_state=PageReview.VISIBLE,
                        is_hidden=False,
                        is_verified=review_data['verified']
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created review for {user.email} (Rating: {review_data["rating"]}/5, Role: {user.role})'))

                # Add helpful votes (randomly)
                if i < 4:  # First 4 reviews get helpful votes
                    other_users = [u for u in test_users if u.id != user.id][:2]
                    for voter in other_users:
                        PageReviewHelpfulVote.objects.get_or_create(
                            review=review,
                            user=voter
                        )
                    review.refresh_from_db()
                    if review.helpful_count > 0:
                        self.stdout.write(f'    - {review.helpful_count} helpful vote(s)')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error for {user.email}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nCompleted!\n'
            f'  Created: {created_count} reviews\n'
            f'  Updated: {updated_count} reviews\n'
            f'  Total: {created_count + updated_count} reviews\n'
            f'  Page: {page.title}\n'
            f'  URL: /pages/{page.public_id}/\n'
        ))













