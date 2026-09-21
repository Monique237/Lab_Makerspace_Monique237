"""Optional fictional sample records. Run with: python seed_demo.py"""
import sqlite3
from datetime import date, timedelta

from database import Database


def seed(db, today=None):
    today = today or date.today()
    examples = [
        ('Alex Demo', 'alex.demo@example.com', 'Demo Camera', 'Media', 'overdue'),
        ('Casey Demo', 'casey.demo@example.com', 'Demo Soldering Kit', 'Electronics', 'returned'),
        ('Sam Demo', 'sam.demo@example.com', 'Demo Laptop', 'Computing', 'available'),
    ]
    for name, email, equipment_name, category, example in examples:
        # The reserved sample email marks an example already added. Never reset it.
        existing = db.connection.execute('SELECT id FROM members WHERE email = ?', (email,)).fetchone()
        if existing:
            continue
        member = db.add_member(name, email)
        item = db.add_equipment(equipment_name, category)
        if example != 'available':
            loan = db.checkout(member.id, item.id, today - timedelta(days=2), today - timedelta(days=7))
            if example == 'returned':
                db.return_loan(loan.id, today - timedelta(days=3))


def main():
    try:
        db = Database()
        try:
            seed(db)
            print('Sample data is ready. Run python main.py to explore it.')
        finally:
            db.close()
    except (ValueError, sqlite3.Error) as error:
        print(f'Could not prepare sample data: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
