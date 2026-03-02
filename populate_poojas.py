"""
Script to populate all poojas in the database.

This script creates all poojas mentioned in the navbar categories:
- Daily & Common Household Poojas
- House, Property & Vehicle Poojas
- Important Life Samskaras (Ceremonies)
- Festival & Temple Poojas
- Homams / Fire Rituals
- Yagnas (Vedic Offerings)

Run this script:
    python populate_poojas.py
"""

import os
import django

# Setup Django - must be done before any imports
# Use same settings module as populate_dummy_data.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

from masterdata.models import Pooja


def populate_all_poojas():
    """Populate all poojas in the database"""
    print("\n📋 Populating All Poojas...")
    
    # All poojas organized by category
    poojas_data = [
        # Daily & Common Household Poojas
        {'name': 'Ganapati Puja', 'description': 'Worship of Lord Ganesha, remover of obstacles'},
        {'name': 'Ganesh Puja', 'description': 'Worship of Lord Ganesha'},
        {'name': 'Ganapathi Puja', 'description': 'Worship of Lord Ganesha'},
        {'name': 'Navagraha Puja', 'description': 'Worship of nine planets for astrological peace'},
        {'name': 'Satyanarayana Vratam', 'description': 'Ritual to please Lord Vishnu for blessings'},
        {'name': 'Satyanarayan Vratam', 'description': 'Ritual to please Lord Vishnu for blessings'},
        {'name': 'Satyanarayana Puja', 'description': 'Worship of Lord Satyanarayana'},
        {'name': 'Lakshmi Puja', 'description': 'Worship of Goddess Lakshmi for wealth'},
        {'name': 'Laxmi Puja', 'description': 'Worship of Goddess Lakshmi for wealth'},
        {'name': 'Durga Puja', 'description': 'Worship of Goddess Durga for protection'},
        {'name': 'Hanuman Puja', 'description': 'Worship of Lord Hanuman for strength'},
        {'name': 'Rudrabhishekam', 'description': 'Special worship of Lord Shiva'},
        {'name': 'Rudra Abhishekam', 'description': 'Special worship of Lord Shiva'},
        {'name': 'Rudra Puja', 'description': 'Worship of Lord Shiva'},
        
        # House, Property & Vehicle Poojas
        {'name': 'Bhoomi Puja', 'description': 'Worship and respect for the land'},
        {'name': 'Gruha Pravesam', 'description': 'Housewarming ceremony before moving in'},
        {'name': 'Gruha Pravesh', 'description': 'Housewarming ceremony before moving in'},
        {'name': 'Vastu Shanti Puja', 'description': 'Correcting vastu doshas for harmony'},
        {'name': 'Vehicle Puja', 'description': 'Worship of vehicles for safety'},
        
        # Important Life Samskaras (Ceremonies)
        {'name': 'Namakarana', 'description': 'Baby naming ceremony'},
        {'name': 'Namkaran', 'description': 'Baby naming ceremony'},
        {'name': 'Annaprashanam', 'description': 'First feeding ceremony for baby'},
        {'name': 'Upanayanam', 'description': 'Sacred thread ceremony for boys'},
        {'name': 'Vivaha Puja', 'description': 'Wedding rituals'},
        {'name': 'Vivah Puja', 'description': 'Wedding rituals'},
        {'name': 'Saptapadi', 'description': 'Seven steps ceremony during weddings'},
        
        # Festival & Temple Poojas
        {'name': 'Vinayaka Chaturthi', 'description': 'Festival worship of Lord Ganesha'},
        {'name': 'Navaratri Puja', 'description': 'Nine nights festival in honor of Goddess Durga'},
        {'name': 'Navratri Puja', 'description': 'Nine nights festival in honor of Goddess Durga'},
        {'name': 'Diwali Puja', 'description': 'Festival of lights, worship of Lakshmi & Ganesha'},
        {'name': 'Deepavali Puja', 'description': 'Festival of lights, worship of Lakshmi & Ganesha'},
        
        # Homams / Fire Rituals
        {'name': 'Ganapathi Homam', 'description': 'Fire ritual to invoke Lord Ganesha'},
        {'name': 'Ganapati Homam', 'description': 'Fire ritual to invoke Lord Ganesha'},
        {'name': 'Navagraha Homam', 'description': 'Homa for nine planets'},
        {'name': 'Mrityunjaya Homam', 'description': 'Powerful fire ritual for health and longevity'},
        {'name': 'Durga Homam', 'description': 'Fire ritual inviting Goddess Durga'},
        
        # Yagnas (Vedic Offerings)
        {'name': 'Satyanarayana Yagna', 'description': 'Special yajna for prosperity and blessings'},
        {'name': 'Satyanarayana Yajna', 'description': 'Special yajna for prosperity and blessings'},
        {'name': 'Putrakameshti Yagna', 'description': 'Yagna to pray for a male child'},
        {'name': 'Putrakameshti Yajna', 'description': 'Yagna to pray for a male child'},
        {'name': 'Ashvamedha Yagna', 'description': 'Ancient royal horse sacrifice yajna'},
        {'name': 'Ashvamedha Yajna', 'description': 'Ancient royal horse sacrifice yajna'},
    ]
    
    created_count = 0
    existing_count = 0
    
    for pooja_data in poojas_data:
        pooja, created = Pooja.objects.get_or_create(
            name=pooja_data['name'],
            defaults={
                'description': pooja_data['description'],
                'is_active': True
            }
        )
        if created:
            print(f"  ✅ Created pooja: {pooja.name}")
            created_count += 1
        else:
            # Update existing pooja to ensure it's active
            if not pooja.is_active:
                pooja.is_active = True
                pooja.save()
                print(f"  🔄 Activated pooja: {pooja.name}")
            else:
                print(f"  ℹ️  Pooja already exists: {pooja.name}")
            existing_count += 1
    
    print(f"\n✅ Pooja Population Complete!")
    print(f"   Created: {created_count}")
    print(f"   Existing: {existing_count}")
    print(f"   Total: {created_count + existing_count}")
    
    # Display all active poojas
    all_poojas = Pooja.objects.filter(is_active=True).order_by('name')
    print(f"\n📋 All Active Poojas ({all_poojas.count()}):")
    for pooja in all_poojas:
        print(f"   - {pooja.name}")


if __name__ == '__main__':
    populate_all_poojas()

