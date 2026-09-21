"""Exercise real menus; only keyboard input is simulated."""
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from database import Database
from main import run, main


class CLITests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = Database(Path(folder.name) / 'test.db')
        self.addCleanup(self.db.close)

    def enter(self, answers):
        output = StringIO()
        with patch('builtins.input', side_effect=answers), redirect_stdout(output):
            run(self.db)
        return output.getvalue()

    def test_full_menu_workflow(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        answers = [
            '1', '1', 'Ada', 'ada@example.com', '2',
            '3', '1', 'Ada Updated', '', '4', '1', '5', '1', '0',
            '2', '1', 'Camera', 'Media', '2', '3', '1', 'Camera Updated', '',
            '4', '1', 'maintenance', '4', '1', 'available', '0',
            '4', '1', 'ada', '2', '1', '3', 'camera', '4', '1', '0',
            '3', '1', '1', '1', tomorrow, '3', '0',
            '5', '1', '2', '3', '1', '0',
            '3', '2', '1', '3', '0', '0',
        ]
        output = self.enter(answers)
        self.assertNotIn('Error:', output)
        self.assertEqual(self.db.get_member(1).name, 'Ada Updated')
        self.assertEqual(self.db.get_member(1).email, 'ada@example.com')
        self.assertTrue(self.db.get_member(1).active)
        self.assertEqual(self.db.get_equipment(1).name, 'Camera Updated')
        self.assertEqual(self.db.get_equipment(1).category, 'Media')
        self.assertTrue(self.db.get_equipment(1).is_available())
        self.assertEqual(self.db.get_loan(1).returned_date, date.today())
        self.assertIn('Ada Updated', output)
        self.assertIn('Camera Updated', output)

    def test_bad_ids_and_menu_choices_do_not_crash(self):
        output = self.enter(['bad', '1', 'bad', '3', 'abc', '3', '0',
                             '3', '-2', '3', '999', '0', '0'])
        self.assertIn('Invalid', output)
        self.assertIn('Error:', output)
        self.assertEqual(self.db.list_members(), [])

    def test_invalid_fields_can_be_corrected(self):
        output = self.enter(['1', '1', '', 'a@example.com',
                             '1', 'Ada', 'not-an-email',
                             '1', 'Ada', 'a@example.com',
                             '1', 'Other', 'A@example.com', '0', '0'])
        self.assertIn('Error:', output)
        self.assertEqual(len(self.db.list_members()), 1)

    def test_invalid_dates_and_unavailable_equipment(self):
        self.db.add_member('Ada', 'ada@example.com')
        self.db.add_equipment('Camera', 'Media')
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        output = self.enter(['3', '1', '1', '1', '2026-02-30',
                             '1', '1', '1', '20260922',
                             '1', '1', '1', '2000-01-01',
                             '1', '1', '1', tomorrow,
                             '1', '1', '1', tomorrow,
                             '2', '1', '2', '1', '0', '0'])
        self.assertIn('Error:', output)
        self.assertEqual(len(self.db.list_loans()), 1)
        self.assertTrue(self.db.get_equipment(1).is_available())

    def test_empty_lists_reports_and_searches(self):
        self.db.add_member('Ada', 'ada@example.com')
        output = self.enter(['2', '2', '0', '3', '3', '0',
                             '4', '1', 'nobody', '2', '999', '0',
                             '5', '1', '2', '3', '1', '0', '0'])
        self.assertIn('No records found.', output)
        self.assertNotIn('Error:', output)

    def test_eof_and_keyboard_interrupt_exit_cleanly(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption):
                output = StringIO()
                with patch('builtins.input', side_effect=interruption), redirect_stdout(output):
                    run(self.db)
                self.assertIn('Goodbye', output.getvalue())

    def test_startup_failure_has_clear_message(self):
        output = StringIO()
        with patch('main.Database', side_effect=sqlite3.OperationalError('unable to open database file')):
            with redirect_stdout(output):
                result = main()
        self.assertEqual(result, 1)
        self.assertIn('database', output.getvalue().lower())
        self.assertNotIn('Traceback', output.getvalue())

    def test_database_lock_is_reported_and_menu_survives(self):
        self.db.connection.execute('PRAGMA busy_timeout = 1')
        other = sqlite3.connect(self.db.path)
        try:
            other.execute('BEGIN IMMEDIATE')
            output = self.enter(['1', '1', 'Ada', 'ada@example.com', '0', '0'])
            self.assertIn('Error:', output)
            self.assertEqual(self.db.list_members(), [])
        finally:
            other.rollback()
            other.close()

    def test_subprocess_uses_script_directory_and_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = root / 'app'
            app.mkdir()
            source = Path(__file__).resolve().parents[1]
            for name in ('main.py', 'models.py', 'database.py'):
                shutil.copyfile(source / name, app / name)
            command = [sys.executable, str(app / 'main.py')]
            first = subprocess.run(command, input='1\n1\nAda\nada@example.com\n0\n0\n',
                                   cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((app / 'makerspace.db').exists())
            self.assertFalse((root / 'makerspace.db').exists())
            second = subprocess.run(command, input='1\n2\n', cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn('Ada', second.stdout)
            self.assertIn('Goodbye', second.stdout)
            self.assertNotIn('Traceback', second.stderr)


if __name__ == '__main__':
    unittest.main()
