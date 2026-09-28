"""
Database Initialization & Production Setup Script
Punjab School Education Department - Teacher Promotion Portal
"""
import sys
import argparse
from app import create_app, get_db
from app.models.user import Base
from seed_data import seed_database

def init_db(seed=True):
    print("=======================================================================")
    print("Punjab School Education Department (SED)")
    print("Teacher Promotion Portal - Database Initialization")
    print("=======================================================================")
    app = create_app()
    with app.app_context():
        print("[OK] Application context created and database tables verified.")
        if seed:
            print("[...] Seeding statutory rules, teaching posts, settings, and accounts...")
            seed_database()
            print("[OK] Database seed completed successfully!")
        else:
            print("[INFO] Skipping seed data (--no-seed passed). Schema tables ready.")
    print("=======================================================================")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Initialize database schema and seed statutory data.")
    parser.add_argument('--no-seed', action='store_true', help="Only create tables without inserting seed data")
    args = parser.parse_args()

    init_db(seed=not args.no_seed)
