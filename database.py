"""SQLite schema, CRUD operations, and SQL reports."""
import sqlite3
from datetime import date
from pathlib import Path

from models import Member, Equipment, Loan, required_text


SCHEMA = '''
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(email)) > 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    category TEXT NOT NULL CHECK (length(trim(category)) > 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'borrowed', 'maintenance', 'retired'))
);
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id),
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    checkout_date TEXT NOT NULL,
    due_date TEXT NOT NULL CHECK (due_date >= checkout_date),
    returned_date TEXT CHECK (returned_date IS NULL OR returned_date >= checkout_date)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_loan_per_item
    ON loans(equipment_id) WHERE returned_date IS NULL;
'''

# JOIN obtains names from their original tables instead of duplicating them in loans.
REPORT_SQL = '''
SELECT l.id AS loan_id, m.name AS member_name, e.name AS equipment_name,
       l.checkout_date, l.due_date, l.returned_date
FROM loans AS l
JOIN members AS m ON m.id = l.member_id
JOIN equipment AS e ON e.id = l.equipment_id
'''


def positive_id(value):
    """Accept positive SQLite integer IDs, with a friendly error for bad input."""
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise ValueError('Enter a positive whole-number ID.') from None
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        raise ValueError('Enter a positive whole-number ID within the supported range.')
    return value


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).with_name('makerspace.db')
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute('PRAGMA foreign_keys = ON')
            self.connection.executescript(SCHEMA)
        except sqlite3.Error:
            self.connection.close()
            raise

    def close(self):
        self.connection.close()

    def get_member(self, id):
        row = self.connection.execute('SELECT * FROM members WHERE id = ?', (positive_id(id),)).fetchone()
        if row is None:
            raise ValueError('Member not found. List members to check the ID.')
        return Member(**dict(row))

    def list_members(self):
        return [Member(**dict(row)) for row in self.connection.execute('SELECT * FROM members ORDER BY id')]

    def add_member(self, name, email):
        member = Member(None, name, email)
        try:
            with self.connection:
                cursor = self.connection.execute('INSERT INTO members (name, email) VALUES (?, ?)',
                                                 (member.name, member.email))
                member.id = cursor.lastrowid
        except sqlite3.IntegrityError as error:
            if 'members.email' in str(error):
                raise ValueError('A member with this email already exists.') from None
            raise
        return member

    def update_member(self, id, name, email):
        member = self.get_member(id)
        member.update(name, email)
        try:
            with self.connection:
                self.connection.execute('UPDATE members SET name = ?, email = ? WHERE id = ?',
                                        (member.name, member.email, member.id))
        except sqlite3.IntegrityError as error:
            if 'members.email' in str(error):
                raise ValueError('A member with this email already exists.') from None
            raise

    def set_member_active(self, id, active):
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            member = self.get_member(id)
            if active:
                member.reactivate()
            else:
                open_loan = self.connection.execute(
                    'SELECT id FROM loans WHERE member_id = ? AND returned_date IS NULL',
                    (member.id,)).fetchone()
                member.deactivate(open_loan is not None)
            self.connection.execute('UPDATE members SET active = ? WHERE id = ?',
                                    (int(member.active), member.id))

    def get_equipment(self, id):
        row = self.connection.execute('SELECT * FROM equipment WHERE id = ?', (positive_id(id),)).fetchone()
        if row is None:
            raise ValueError('Equipment not found. List equipment to check the ID.')
        return Equipment(**dict(row))

    def list_equipment(self):
        return [Equipment(**dict(row)) for row in self.connection.execute('SELECT * FROM equipment ORDER BY id')]

    def add_equipment(self, name, category):
        item = Equipment(None, name, category)
        with self.connection:
            cursor = self.connection.execute('INSERT INTO equipment (name, category) VALUES (?, ?)',
                                             (item.name, item.category))
            item.id = cursor.lastrowid
        return item

    def update_equipment(self, id, name, category):
        item = self.get_equipment(id)
        item.update(name, category)
        with self.connection:
            self.connection.execute('UPDATE equipment SET name = ?, category = ? WHERE id = ?',
                                    (item.name, item.category, item.id))

    def set_equipment_status(self, id, status):
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            item = self.get_equipment(id)
            item.set_status(status)
            self.connection.execute('UPDATE equipment SET status = ? WHERE id = ?', (item.status, item.id))

    @staticmethod
    def loan_from_row(row):
        return Loan(row['id'], row['member_id'], row['equipment_id'],
                    date.fromisoformat(row['checkout_date']), date.fromisoformat(row['due_date']),
                    date.fromisoformat(row['returned_date']) if row['returned_date'] else None)

    def get_loan(self, id):
        row = self.connection.execute('SELECT * FROM loans WHERE id = ?', (positive_id(id),)).fetchone()
        if row is None:
            raise ValueError('Loan not found. List loans to check the ID.')
        return self.loan_from_row(row)

    def list_loans(self):
        return [self.loan_from_row(row) for row in self.connection.execute('SELECT * FROM loans ORDER BY id')]

    def checkout(self, member_id, equipment_id, due_date, checkout_date=None):
        # A transaction saves both changes, or neither if any step fails.
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            member = self.get_member(member_id)
            item = self.get_equipment(equipment_id)
            loan = Loan.create(member, item, due_date, checkout_date)
            cursor = self.connection.execute('''
                INSERT INTO loans (member_id, equipment_id, checkout_date, due_date)
                VALUES (?, ?, ?, ?)
            ''', (member.id, item.id, loan.checkout_date.isoformat(), loan.due_date.isoformat()))
            loan.id = cursor.lastrowid
            self.connection.execute('UPDATE equipment SET status = ? WHERE id = ?', (item.status, item.id))
        return loan

    def return_loan(self, id, returned_date=None):
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            loan = self.get_loan(id)
            item = self.get_equipment(loan.equipment_id)
            loan.close(item, returned_date)
            self.connection.execute('UPDATE loans SET returned_date = ? WHERE id = ?',
                                    (loan.returned_date.isoformat(), loan.id))
            self.connection.execute('UPDATE equipment SET status = ? WHERE id = ?', (item.status, item.id))

    def search_members(self, term, by_id=False):
        if by_id:
            rows = self.connection.execute('SELECT * FROM members WHERE id = ?', (positive_id(term),))
        else:
            term = required_text(term, 'Search text')
            rows = self.connection.execute(
                'SELECT * FROM members WHERE instr(lower(name), lower(?)) > 0 ORDER BY id', (term,))
        return [Member(**dict(row)) for row in rows]

    def search_equipment(self, term, by_id=False):
        if by_id:
            rows = self.connection.execute('SELECT * FROM equipment WHERE id = ?', (positive_id(term),))
        else:
            term = required_text(term, 'Search text')
            rows = self.connection.execute(
                'SELECT * FROM equipment WHERE instr(lower(name), lower(?)) > 0 ORDER BY id', (term,))
        return [Equipment(**dict(row)) for row in rows]

    def borrowed_report(self):
        return self.connection.execute(REPORT_SQL +
            ' WHERE l.returned_date IS NULL ORDER BY l.due_date, l.id').fetchall()

    def overdue_report(self, today=None):
        today = today or date.today()
        return self.connection.execute(REPORT_SQL +
            ' WHERE l.returned_date IS NULL AND l.due_date < ? ORDER BY l.due_date, l.id',
            (today.isoformat(),)).fetchall()

    def member_history(self, member_id):
        member = self.get_member(member_id)
        return self.connection.execute(REPORT_SQL +
            ' WHERE l.member_id = ? ORDER BY l.checkout_date DESC, l.id DESC', (member.id,)).fetchall()
