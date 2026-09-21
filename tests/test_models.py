"""Behaviour checks for the three domain classes."""
import unittest
from datetime import date

from models import Member, Equipment, Loan


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.member = Member(1, ' Ada ', 'ada@example.com')
        self.item = Equipment(1, 'Camera', 'Media')

    def test_member_validation_and_updates(self):
        self.assertEqual(self.member.name, 'Ada')
        self.member.update('Ada Lovelace', 'ADA@example.com')
        self.assertEqual(self.member.email, 'ADA@example.com')
        for name, email in [('', 'a@b.com'), ('Ada', 'bad'), ('Ada', 'a @b.com'),
                            ('Ada', '@b.com'), ('Ada', 'a@.com')]:
            with self.subTest(name=name, email=email), self.assertRaises(ValueError):
                self.member.update(name, email)
        self.assertEqual(self.member.name, 'Ada Lovelace')

    def test_member_activation(self):
        with self.assertRaises(ValueError):
            self.member.deactivate(True)
        self.member.deactivate(False)
        self.assertFalse(self.member.can_borrow())
        self.member.reactivate()
        self.assertTrue(self.member.can_borrow())

    def test_equipment_transitions_and_validation(self):
        self.item.update('Camera A', 'Photography')
        self.assertEqual(self.item.category, 'Photography')
        with self.assertRaises(ValueError):
            self.item.update('', 'Media')
        for status in ['maintenance', 'retired']:
            self.item.set_status(status)
            self.assertFalse(self.item.is_available())
            with self.assertRaises(ValueError):
                self.item.borrow()
        self.item.set_status('available')
        with self.assertRaises(ValueError):
            self.item.set_status('borrowed')
        with self.assertRaises(ValueError):
            self.item.set_status('unknown')
        self.item.borrow()
        with self.assertRaises(ValueError):
            self.item.set_status('available')
        self.item.return_item()
        with self.assertRaises(ValueError):
            self.item.return_item()

    def test_checkout_return_and_overdue_boundary(self):
        loan = Loan.create(self.member, self.item, date(2026, 9, 22), date(2026, 9, 21))
        self.assertFalse(self.item.is_available())
        self.assertFalse(loan.is_overdue(date(2026, 9, 22)))
        self.assertTrue(loan.is_overdue(date(2026, 9, 23)))
        with self.assertRaises(ValueError):
            loan.close(self.item, date(2026, 9, 20))
        with self.assertRaises(ValueError):
            loan.close(Equipment(2, 'Other camera', 'Media', 'borrowed'), date(2026, 9, 23))
        loan.close(self.item, date(2026, 9, 23))
        self.assertTrue(self.item.is_available())
        self.assertFalse(loan.is_overdue(date(2026, 9, 24)))
        with self.assertRaises(ValueError):
            loan.close(self.item, date(2026, 9, 24))

    def test_invalid_checkout_does_not_change_equipment(self):
        with self.assertRaises(ValueError):
            Loan.create(self.member, self.item, date(2026, 9, 20), date(2026, 9, 21))
        self.assertTrue(self.item.is_available())
        self.member.deactivate(False)
        with self.assertRaises(ValueError):
            Loan.create(self.member, self.item, date(2026, 9, 22), date(2026, 9, 21))
        self.assertTrue(self.item.is_available())


if __name__ == '__main__':
    unittest.main()
