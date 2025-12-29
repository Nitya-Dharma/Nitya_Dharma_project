# Nitya Dharma - Pandit Listing Website

A professional Django-based platform for listing and managing Pandits (priests) with controlled onboarding, referral system, and booking capabilities.

## Project Overview

This project follows a strict sequential module architecture to ensure:
- Zero orphan features
- Zero broken connections
- Zero security gaps
- Fully sequential development

## Technology Stack

- **Backend:** Django 4.2+ (LTS)
- **Database:** MySQL
- **Frontend:** Bootstrap
- **Python:** 3.13+

## Project Structure

The project is built in 13 sequential modules:

1. **Module 0** - System Foundation
2. **Module 1** - User & Role System
3. **Module 2** - Pandit Onboarding
4. **Module 3** - Referral & Trust Chain
5. **Module 4** - Pandit Profile
6. **Module 5** - Authorized Dashboard
7. **Module 6** - Availability & Calendar
8. **Module 7** - User Search & Discovery
9. **Module 8** - Booking Intent
10. **Module 9** - Ratings & Reviews
11. **Module 10** - Public Trust Display
12. **Module 11** - Admin Governance
13. **Module 12** - Security Hardening
14. **Module 13** - Performance & Cleanup

## Setup Instructions

### Prerequisites

- Python 3.13+
- MySQL Server
- Git

### Installation

1. **Clone the repository** (if applicable)
   ```bash
   git clone <repository-url>
   cd "Nitya Dharma"
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Copy `.env.example` to `.env` (create if needed)
   - Update with your database credentials and secret key

5. **Database Setup** (will be done in Module 0, Task 0.4)
   - Create MySQL database
   - Configure connection in `.env`

## Development Status

Currently implementing: **Module 0 - System Foundation**

## Architecture Principles

- **Sequential Development:** Each module depends on previous modules
- **Trust Precedes Visibility:** Pandits must be approved before public listing
- **Availability Precedes Search:** Calendar must exist before search functionality
- **Interaction Precedes Review:** Bookings must exist before reviews

## Documentation

Full project documentation and module breakdowns are available in `docs/` directory.

## License

[To be added]

## Contributing

[To be added]













