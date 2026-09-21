# MakerSpace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a simple, explainable terminal application covering the assessment's OOP, SQLite, validation, and demonstration requirements.

**Architecture:** Keep the menu in main.py, three domain classes in models.py, and SQL in database.py. Database methods load objects and use their methods before saving changes in transactions. No GUI, web framework, or additional service layer.

**Tech Stack:** Python 3, sqlite3, datetime, pathlib, unittest, tempfile, subprocess.

**Spec:** ../specs/2026-09-21-makerspace-design.md

## Global Constraints

- Use Python's standard library and SQLite, with no installation of third-party packages.
- Keep the code readable for a first-year student to explain in a live demonstration.
- Do not duplicate member names or equipment descriptions in loans.
- Use parameterised values for all user input.
- An item due today becomes overdue tomorrow.
- Keep all loan history.
- No network, GUI, accounts, fines, reservations, or unrelated features are in scope.
- Keep explanations concise, following the user's request: simple and not complex.
- Git commits are conditional on an existing configured identity; do not invent a name or email or change global Git settings.

## Review Focus

- Names containing apostrophes or SQL wildcard characters must be stored and searched literally (Task 2).
- Failure halfway through checkout must leave both equipment and loans unchanged (Task 2).
- Equipment updates must not erase or bypass an active loan (Task 2).
- Overdue reports must distinguish yesterday, today, and returned loans (Tasks 1 and 2).
- Running from another directory and ending input must not create a second database or display a traceback (Task 3).

## Task 1: Three meaningful domain classes

**Files:** Create models.py and tests/test_models.py.

**Interfaces:** Member(id, name, email, active=True), Equipment(id, name, category, status='available'), Loan(id, member_id, equipment_id, checkout_date, due_date, returned_date=None). Dates are datetime.date objects. Methods below return None unless specified; invalid actions raise ValueError with a useful message.

- Member.update(name, email); Member.can_borrow() -> bool; Member.deactivate(has_open_loans); Member.reactivate().
- Equipment.update(name, category); Equipment.is_available() -> bool; Equipment.borrow(); Equipment.return_item(); Equipment.set_status(status).
- Loan.create(member, equipment, due_date, checkout_date=None) -> Loan with id=None; Loan.close(equipment, returned_date=None); Loan.is_overdue(today=None) -> bool.

- [x] Write unittest cases for blank fields, malformed emails, member activation, equipment transitions, checkout rejection, and returned/overdue boundaries. Representative behaviour:

```python
member = Member(1, 'Ada', 'ada@example.com')
item = Equipment(1, 'Camera', 'Media')
loan = Loan.create(member, item, date(2026, 9, 22), date(2026, 9, 21))
self.assertFalse(item.is_available())
self.assertFalse(loan.is_overdue(date(2026, 9, 22)))
self.assertTrue(loan.is_overdue(date(2026, 9, 23)))
loan.close(item, date(2026, 9, 23))
self.assertTrue(item.is_available())
self.assertFalse(loan.is_overdue(date(2026, 9, 24)))
with self.assertRaises(ValueError):
    loan.close(item, date(2026, 9, 24))
```

- [x] Run `python -m unittest discover -s tests -p test_models.py -v`; confirm failures originate from missing implementation.
- [x] Implement constructors and methods with ordinary classes and readable validation. Check eligibility and dates before changing equipment state. Use simple email validation: one @, nonempty local/domain parts, a dot within the domain, and no whitespace. Keep formatting outside these classes.

```python
def is_overdue(self, today=None):
    today = today or date.today()
    return self.returned_date is None and self.due_date < today
```

- [x] Run the same tests and resolve failures. If Git identity is configured, commit models and tests with `git commit -m "Add MakerSpace domain classes"` after staging only those files.

## Task 2: SQLite storage and business operations

**Files:** Create database.py and tests/test_database.py.

**Consumes:** The three domain classes and methods from Task 1.

**Produces:** Database(path=None), with a public connection attribute for focused SQL tests, close(), and these operations:

- add_member(name, email) -> Member; get_member(id) -> Member; list_members() -> list[Member]; update_member(id, name, email); set_member_active(id, active).
- add_equipment(name, category) -> Equipment; get_equipment(id) -> Equipment; list_equipment() -> list[Equipment]; update_equipment(id, name, category); set_equipment_status(id, status).
- checkout(member_id, equipment_id, due_date, checkout_date=None) -> Loan; get_loan(id) -> Loan; list_loans() -> list[Loan]; return_loan(id, returned_date=None).
- search_members(term, by_id=False) -> list[Member]; search_equipment(term, by_id=False) -> list[Equipment].
- borrowed_report() -> list[sqlite3.Row]; overdue_report(today=None) -> list[sqlite3.Row]; member_history(member_id) -> list[sqlite3.Row]. Report rows expose loan_id, member_name, equipment_name, checkout_date, due_date, returned_date.

- [x] Create tests using TemporaryDirectory and a fresh database per test. Check CRUD/status changes, reopened persistence, foreign keys, duplicate emails ignoring case, restrictions during active loans, SQL searches, report contents and dates, and repeated return rejection. Representative workflow:

```python
member = self.db.add_member("O'Neil", 'oneil@example.com')
item = self.db.add_equipment('Camera 100%', 'Media')
loan = self.db.checkout(member.id, item.id, date(2026, 9, 22), date(2026, 9, 21))
with self.assertRaises(ValueError):
    self.db.checkout(member.id, item.id, date(2026, 9, 22))
self.assertEqual(len(self.db.overdue_report(date(2026, 9, 22))), 0)
self.assertEqual(len(self.db.overdue_report(date(2026, 9, 23))), 1)
self.assertEqual(len(self.db.search_equipment('%')), 1)
self.db.return_loan(loan.id, date(2026, 9, 23))
self.assertEqual(len(self.db.borrowed_report()), 0)
```

- [x] Run `python -m unittest discover -s tests -p test_database.py -v` and observe failure before implementation.
- [x] Create the schema exactly as specified. Use pathlib to default to makerspace.db beside database.py, enable foreign keys, use sqlite3.Row, ISO date strings, CHECK constraints, and a partial unique index for open loans. Map rows to model objects in small helper methods. Use case-insensitive literal substring search with instr(lower(name), lower(?)), and exact numeric ID search.

```sql
CREATE UNIQUE INDEX IF NOT EXISTS one_open_loan_per_item
ON loans(equipment_id) WHERE returned_date IS NULL;
```

- [x] Implement operations with parameterised SQL. Acquire the write transaction before checkout/return reads; use models for business rules; persist loan and equipment together; roll back on errors. Include the three reports as SQL JOIN queries ordered by dates/IDs.

```python
with self.connection:
    self.connection.execute('BEGIN IMMEDIATE')
    member = self.get_member(member_id)
    equipment = self.get_equipment(equipment_id)
    loan = Loan.create(member, equipment, due_date, checkout_date)
    cursor = self.connection.execute(
        'INSERT INTO loans (member_id, equipment_id, checkout_date, due_date) VALUES (?, ?, ?, ?)',
        (member.id, equipment.id, loan.checkout_date.isoformat(), loan.due_date.isoformat()),
    )
    loan.id = cursor.lastrowid
    self.connection.execute('UPDATE equipment SET status = ? WHERE id = ?',
                            (equipment.status, equipment.id))
return loan
```

- [x] Add a database trigger in a test to force failure on the equipment UPDATE during checkout. Assert both the new loan and status update are rolled back. Add equivalent return consistency coverage and a direct duplicate-open-loan INSERT check.

```sql
CREATE TRIGGER reject_equipment_update BEFORE UPDATE ON equipment
BEGIN SELECT RAISE(ABORT, 'forced test failure'); END;
```

- [x] Run `python -m unittest discover -s tests -v` and fix failures. Commit the storage implementation and tests if Git identity is available.

## Task 3: Menus, sample data, and assessment documentation

**Files:** Fill main.py; create seed_demo.py, tests/test_cli.py, tests/test_seed.py, README.md, and .gitignore.

**Consumes:** Database and domain interfaces from Tasks 1–2.

**Produces:** main.run(db=None) for the interactive menu (injected databases remain caller-owned), main.main() for clean startup/shutdown, seed_demo.seed(db, today=None) for optional sample data. Both scripts use an `if __name__ == '__main__':` entry point.

- [x] Write tests for a full scripted registration → editing → search → checkout → reports → return workflow, invalid menu choices/IDs/dates, blank updates preserving values, keyboard interruption and EOF, empty reports, and startup failure. Use unittest.mock.patch for input and redirect_stdout for output. Check actual stored results, not just output messages.

```python
with patch('builtins.input', side_effect=['bad', '0']):
    with redirect_stdout(StringIO()) as output:
        run(self.db)
self.assertIn('Invalid', output.getvalue())
```

- [x] Test sample setup twice in a temporary database. Confirm unchanged record counts, no resets of existing records, and sample rows for current borrowing, overdue, and returned history.
- [x] Run tests to confirm the new files/entry points are missing before implementation.
- [x] Implement small submenu functions with explicit numbered options and Back/Exit as 0. Convert IDs with int and dates with date.fromisoformat. Catch expected ValueError/sqlite3.Error at the menu boundary and print useful messages; handle EOFError/KeyboardInterrupt at the application boundary. Do not add broad catch-all handlers. Show IDs in listings so the user can select records.

```python
def read_id(prompt):
    value = int(input(prompt))
    if value <= 0:
        raise ValueError('Please enter a positive ID.')
    return value
```

- [x] Implement seed() with unique fictional sample emails and explicit equipment lookups. Create records only when absent. Use dates relative to today for one overdue and one returned sample loan, and skip existing sample history so repeated runs do not re-borrow returned items.
- [x] Write README instructions for running, sample data, tests, tables/classes, all menus, literal search, status updates instead of deletion, and the demo sequence. Include an honest acknowledgement that OpenAI Codex assisted with design, code, tests, and documentation when applicable. State that the student must understand and adapt the code under the assessment rules. Include submission checklist with exact public repository naming format and outstanding Canvas/demo steps.
- [x] Add generated-file exclusions:

```gitignore
__pycache__/
*.py[cod]
*.db
*.db-journal
*.db-wal
*.db-shm
.venv/
```

- [x] Run `python -m unittest discover -s tests -v`, plus a subprocess CLI smoke test from a different working directory using an isolated copy of the scripts. Verify the database appears beside the copied scripts, persists after restarting, and EOF exits without traceback. Inspect `git diff --check` and project-only `git status --short`.
- [x] Review each rubric requirement against the finished files. If a test fails, diagnose and fix the root cause, then rerun relevant tests. Commit only project files if identity is configured; otherwise report that commits remain pending without blocking local usage.
- [x] Deliver the local run command, important file links, observed test result, and remaining student-owned demo/submission steps. Never claim a guaranteed grade or completed external submission.

## Self-review

All required assessment features map to Tasks 1–3. The five review-focus conditions have explicit checks. Domain methods, database operations, and CLI entry points use consistent names. No new packages, GUI, or unrelated functions are planned.
