import tempfile
import unittest
from datetime import date
from pathlib import Path

from database import Database
from seed_demo import seed


class SeedTests(unittest.TestCase):
    def test_seed_is_repeat_safe_and_preserves_existing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / 'sample.db')
            try:
                existing = db.add_member('Existing user', 'existing@example.com')
                existing_item = db.add_equipment('My camera', 'Media')
                seed(db, date(2026, 9, 21))
                self.assertEqual(len(db.list_members()), 4)
                self.assertEqual(len(db.list_equipment()), 4)
                self.assertEqual(len(db.list_loans()), 2)
                self.assertEqual(len(db.overdue_report(date(2026, 9, 21))), 1)
                open_id = db.borrowed_report()[0]['loan_id']
                db.return_loan(open_id, date(2026, 9, 21))
                seed(db, date(2026, 9, 22))
                self.assertEqual(len(db.list_members()), 4)
                self.assertEqual(len(db.list_equipment()), 4)
                self.assertEqual(len(db.list_loans()), 2)
                self.assertEqual(db.borrowed_report(), [])
                self.assertEqual(db.get_member(existing.id).name, 'Existing user')
                self.assertEqual(db.get_equipment(existing_item.id).name, 'My camera')
            finally:
                db.close()


if __name__ == '__main__':
    unittest.main()
