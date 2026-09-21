"""Integration tests use real SQLite files in temporary folders."""
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'test.db'
        self.db = Database(self.path)
        self.addCleanup(self.db.close)
        self.member = self.db.add_member("O'Neil", 'oneil@example.com')
        self.item = self.db.add_equipment('Camera 100%', 'Media')

    def borrow(self):
        return self.db.checkout(self.member.id, self.item.id,
                                date(2026, 9, 22), date(2026, 9, 21))

    def test_member_crud_and_persistence(self):
        self.db.update_member(self.member.id, 'New Name', 'new@example.com')
        self.db.set_member_active(self.member.id, False)
        with self.assertRaises(ValueError):
            self.borrow()
        self.assertEqual(len(self.db.list_members()), 1)
        self.db.close()
        other = Database(self.path)
        self.addCleanup(other.close)
        member = other.get_member(self.member.id)
        self.assertEqual(member.name, 'New Name')
        self.assertFalse(member.active)
        other.set_member_active(member.id, True)
        self.assertTrue(other.get_member(member.id).can_borrow())

    def test_equipment_crud_and_status(self):
        self.db.update_equipment(self.item.id, 'Camera A', 'Photography')
        self.db.set_equipment_status(self.item.id, 'maintenance')
        self.assertEqual(self.db.get_equipment(self.item.id).name, 'Camera A')
        self.assertEqual(len(self.db.list_equipment()), 1)
        with self.assertRaises(ValueError):
            self.borrow()
        self.db.set_equipment_status(self.item.id, 'retired')
        with self.assertRaises(ValueError):
            self.borrow()
        self.db.set_equipment_status(self.item.id, 'available')
        self.assertTrue(self.db.get_equipment(self.item.id).is_available())

    def test_case_insensitive_duplicate_email(self):
        with self.assertRaisesRegex(ValueError, 'email'):
            self.db.add_member('Duplicate', 'ONEIL@example.com')
        second = self.db.add_member('Second', 'second@example.com')
        with self.assertRaisesRegex(ValueError, 'email'):
            self.db.update_member(second.id, 'Changed', 'ONEIL@example.com')
        self.assertEqual(self.db.get_member(second.id).name, 'Second')

    def test_search_by_id_and_literal_name(self):
        self.db.add_equipment('Camera normal', 'Media')
        self.assertEqual([x.id for x in self.db.search_members("o'ne")], [self.member.id])
        self.assertEqual(len(self.db.search_equipment('%')), 1)
        self.assertEqual(self.db.search_equipment('_'), [])
        self.assertEqual(self.db.search_members("' OR 1=1 --"), [])
        self.assertEqual(self.db.search_members(str(self.member.id), True)[0].id, self.member.id)
        self.assertEqual(self.db.search_equipment(str(self.item.id), True)[0].id, self.item.id)
        self.assertEqual(self.db.search_members('999', True), [])
        for term in ('', '0', '-1', 'abc'):
            with self.subTest(term=term), self.assertRaises(ValueError):
                self.db.search_members(term, True)
        with self.assertRaises(ValueError):
            self.db.search_equipment('   ')

    def test_missing_records_and_bad_ids(self):
        for getter in (self.db.get_member, self.db.get_equipment, self.db.get_loan):
            for id in (999, 0, -1, 'bad', 1.5, 10**100):
                with self.subTest(getter=getter.__name__, id=id), self.assertRaises(ValueError):
                    getter(id)
        with self.assertRaises(ValueError):
            self.db.checkout(999, self.item.id, date(2026, 9, 22))
        with self.assertRaises(ValueError):
            self.db.checkout(self.member.id, 999, date(2026, 9, 22))
        with self.assertRaises(ValueError):
            self.db.member_history(999)

    def test_invalid_due_date_leaves_item_available(self):
        with self.assertRaises(ValueError):
            self.db.checkout(self.member.id, self.item.id,
                             date(2026, 9, 20), date(2026, 9, 21))
        self.assertEqual(self.db.list_loans(), [])
        self.assertTrue(self.db.get_equipment(self.item.id).is_available())

    def test_checkout_return_and_restart(self):
        loan = self.borrow()
        self.db.close()
        self.db = Database(self.path)
        self.addCleanup(self.db.close)
        self.assertFalse(self.db.get_equipment(self.item.id).is_available())
        self.assertEqual(self.db.get_loan(loan.id).member_id, self.member.id)
        self.assertEqual(len(self.db.list_loans()), 1)
        self.db.return_loan(loan.id, date(2026, 9, 23))
        self.assertTrue(self.db.get_equipment(self.item.id).is_available())
        self.assertEqual(self.db.get_loan(loan.id).returned_date, date(2026, 9, 23))
        with self.assertRaises(ValueError):
            self.db.return_loan(loan.id)

    def test_open_loan_restricts_member_and_equipment_updates(self):
        loan = self.borrow()
        with self.assertRaises(ValueError):
            self.borrow()
        with self.assertRaises(ValueError):
            self.db.set_member_active(self.member.id, False)
        for status in ('available', 'maintenance', 'retired', 'borrowed'):
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.db.set_equipment_status(self.item.id, status)
        self.db.update_equipment(self.item.id, 'Renamed camera', 'Media')
        self.assertEqual(self.db.get_equipment(self.item.id).status, 'borrowed')
        self.db.return_loan(loan.id, date(2026, 9, 23))
        self.db.set_member_active(self.member.id, False)
        self.db.set_equipment_status(self.item.id, 'retired')
        self.assertEqual(len(self.db.member_history(self.member.id)), 1)

    def test_sql_reports_and_date_boundaries(self):
        loan = self.borrow()
        rows = self.db.borrowed_report()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['member_name'], "O'Neil")
        self.assertEqual(rows[0]['equipment_name'], 'Camera 100%')
        self.assertEqual(self.db.overdue_report(date(2026, 9, 22)), [])
        self.assertEqual(len(self.db.overdue_report(date(2026, 9, 23))), 1)
        self.db.return_loan(loan.id, date(2026, 9, 23))
        self.assertEqual(self.db.borrowed_report(), [])
        self.assertEqual(self.db.overdue_report(date(2026, 9, 24)), [])
        self.assertEqual(self.db.member_history(self.member.id)[0]['returned_date'], '2026-09-23')

    def reject_equipment_updates(self):
        self.db.connection.execute('''
            CREATE TRIGGER reject_update BEFORE UPDATE ON equipment
            BEGIN SELECT RAISE(ABORT, 'forced failure'); END
        ''')

    def test_checkout_failure_rolls_back_loan_and_status(self):
        self.reject_equipment_updates()
        with self.assertRaises(sqlite3.IntegrityError):
            self.borrow()
        self.assertEqual(self.db.list_loans(), [])
        self.assertTrue(self.db.get_equipment(self.item.id).is_available())

    def test_return_failure_rolls_back_loan_and_status(self):
        loan = self.borrow()
        self.reject_equipment_updates()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.return_loan(loan.id, date(2026, 9, 23))
        self.assertIsNone(self.db.get_loan(loan.id).returned_date)
        self.assertEqual(self.db.get_equipment(self.item.id).status, 'borrowed')

    def test_schema_blocks_duplicate_open_loan_and_invalid_foreign_keys(self):
        self.borrow()
        sql = 'INSERT INTO loans (member_id,equipment_id,checkout_date,due_date) VALUES (?,?,?,?)'
        for member_id, item_id in [(self.member.id, self.item.id), (999, 999)]:
            with self.assertRaises(sqlite3.IntegrityError), self.db.connection:
                self.db.connection.execute(sql, (member_id, item_id, '2026-09-21', '2026-09-22'))

    def test_second_connection_cannot_borrow_same_item(self):
        other = Database(self.path)
        self.addCleanup(other.close)
        self.borrow()
        with self.assertRaises(ValueError):
            other.checkout(self.member.id, self.item.id, date(2026, 9, 22), date(2026, 9, 21))
        self.assertEqual(len(other.list_loans()), 1)


if __name__ == '__main__':
    unittest.main()
