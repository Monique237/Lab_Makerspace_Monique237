# Campus MakerSpace Checkout System

A simple Python terminal application for registering members and equipment, borrowing and returning items, searching records, and showing SQL reports. Data is saved in SQLite between runs.

## Start here

Use Python 3.10 or newer. There are **no extra packages to install**; `sqlite3` comes with Python. Tested locally with Python 3.14.7 on Windows.

Open a terminal in this project folder and run:

```powershell
python main.py
```

If your Windows installation uses the Python launcher, use `py main.py` instead.

The application creates `makerspace.db` beside the Python files on its first run. The database stays in that folder even if you launch the script from elsewhere. Each successful change is saved immediately. Choose `0` to go back or exit.

Optional fictional sample data:

```powershell
python seed_demo.py
python main.py
```

This adds Alex Demo with an overdue camera loan, Casey Demo with a returned soldering kit, and Sam Demo with an available laptop. Dates are relative to the day the sample script runs. Existing sample emails are skipped on later runs so existing examples are not reset. Do not change the reserved `*.demo@example.com` emails if you want that repeat protection. Your other records remain unchanged.

If sample setup is interrupted after creating a member, rerunning does not repair that incomplete example. For a fresh demonstration, use a separate practice copy of the Python files without copying the database. Normal application checkout and return operations are transactional.

## Main menu

```text
1. Members
2. Equipment
3. Loans
4. Search
5. Reports
0. Exit
```

| Menu | Features |
| --- | --- |
| Members | Register, list, update name/email, deactivate, reactivate |
| Equipment | Register, list, update name/category, change status |
| Loans | Checkout, return using the loan ID, list all loans |
| Search | Members or equipment by exact ID or part of their name |
| Reports | Currently borrowed items, overdue loans, member loan history |

Enter dates as `YYYY-MM-DD`. Checkout uses today's date; the due date can be today or later. An open loan becomes overdue on the day after its due date. When updating details, leave a prompt blank to keep its current value.

Names are searched as literal substrings: `%` and `_` are ordinary characters. Matching ignores ASCII letter case using SQLite's built-in `lower()`.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | Menu loops, prompts, output, and friendly error handling |
| `models.py` | Member, Equipment, and Loan objects and their rules |
| `database.py` | Database connection, automatic schema, CRUD, and SQL reports |
| `seed_demo.py` | Optional fictional sample records |
| `tests/` | Automated checks with temporary databases |
| `docs/superpowers/` | Design and implementation planning notes |

## OOP: three meaningful classes

| Class | Attributes | Examples of behaviour |
| --- | --- | --- |
| `Member` | id, name, email, active | `update()`, `can_borrow()`, `deactivate()`, `reactivate()` |
| `Equipment` | id, name, category, status | `update()`, `is_available()`, `borrow()`, `return_item()`, `set_status()` |
| `Loan` | id, member_id, equipment_id, checkout_date, due_date, returned_date | `create()`, `close()`, `is_overdue()` |

`Database` is a fourth class that keeps SQL separate from the menus and domain rules.

**Object collaboration during checkout:** the menu calls `Database.checkout()`. It loads a Member and Equipment, then passes those objects to `Loan.create()`. The loan checks `member.can_borrow()` and calls `equipment.borrow()`. The database saves the new loan and the equipment's new status together.

**During return:** the database loads the Loan and Equipment, calls `loan.close(equipment)`, and saves both changes. `close()` calls `equipment.return_item()`. These methods keep the rules in the relevant classes instead of duplicating them in menu code.

`@classmethod` on `Loan.create()` means it constructs and returns a new Loan. Other methods, such as `close()`, work on an existing object. Inheritance is not necessary because a member, an item, and a loan are different kinds of things.

## Database design and CRUD

The full schema is the `SCHEMA` string in `database.py` and runs automatically on startup.

| Table | Stored fields |
| --- | --- |
| members | id (primary key), name, email (unique), active |
| equipment | id (primary key), name, category, status |
| loans | id (primary key), member_id and equipment_id (foreign keys), checkout_date, due_date, returned_date |

One member can have many loans. One equipment item can have many historical loans but only one open loan. Foreign keys connect those tables, and a unique partial index enforces the one-open-loan rule. Names and categories stay in their original tables; loans store their IDs.

| CRUD operation | Application example |
| --- | --- |
| Create | Register a member/item; create a loan using `INSERT` |
| Read | Lists, searches, and reports using `SELECT` |
| Update | Edit details, checkout status, and return dates using `UPDATE` |
| Delete equivalent | Deactivate members or retire equipment; close loans while preserving history |

The assessment explicitly permits status updates instead of deletion. Members with open loans cannot be deactivated. Borrowed equipment cannot be retired or put into maintenance until returned. Only checkout sets an item to `borrowed`; return restores it to `available`.

**Transactions:** checkout and return each save two related changes. `BEGIN IMMEDIATE` reserves the write transaction before checking the stored state. The connection context manager commits when all statements succeed and rolls back if a step fails. This prevents a loan from being saved without its corresponding equipment update.

**Parameterised SQL:** statements use `?` placeholders with separate values, for example:

```python
connection.execute('SELECT * FROM members WHERE id = ?', (member_id,))
```

This treats input as data, including names with apostrophes, and avoids building SQL from user-entered text.

## Three SQL reports

All three use `JOIN` to connect loans to members and equipment and show readable names.

1. **Currently borrowed:** `WHERE l.returned_date IS NULL`, ordered by due date and loan ID.
2. **Overdue:** `WHERE l.returned_date IS NULL AND l.due_date < ?`, with today's ISO date supplied as the parameter.
3. **Member history:** `WHERE l.member_id = ?`, including both open and returned loans, newest first.

The shared `REPORT_SQL` query and the three report methods are in `database.py`. ISO date strings sort in chronological order. `NULL` in `returned_date` means the loan is still open.

## Validation and testing

The application checks blank required fields, simple email format, duplicate emails regardless of ASCII case, menu choices, positive integer IDs, nonexistent records, real calendar dates, due dates before checkout, inactive members, unavailable equipment, and repeated returns. Email validation checks basic structure; it does not verify that a mailbox exists.

Expected input and database errors show a message. The menu stays usable; Ctrl+C or the end of input exits cleanly. Failure to open or initialise the database gives a clear startup message.

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

Tests use temporary databases and do not change your own `makerspace.db`. They cover class behaviour, persistence after reopening, all menu features, rejected actions, literal searches, SQL reports, sample data, and transaction rollback when a database update fails. A subprocess test starts the app from another directory and checks saved data on a second run.

## Live demo walkthrough

Practise this before your class/coaching slot. Use the actual IDs shown by the app; they may differ from a new database.

1. Run `python seed_demo.py`, then `python main.py`.
2. **Members:** list samples; register yourself with a sample email; update your name; list again. Show deactivation and reactivation before borrowing.
3. **Equipment:** register a new item; update its details; list it. Set it to maintenance and back to available.
4. **Search:** find your member by part of the name and by ID. Repeat for equipment.
5. **Loans:** check out your available item to your active member. Choose tomorrow's date. Note the loan ID and list loans.
6. Attempt to borrow the same item again. Explain the clear rejection. Try a nonexistent member ID or invalid date to demonstrate validation.
7. **Reports:** show currently borrowed items, overdue sample loans, and your member's history. Explain the JOIN and filtering used.
8. **Loans:** return your loan. List equipment to show it is available. Try the same return again to demonstrate the protection.
9. Retire your returned item or deactivate your member, then show that the loan history remains.
10. Exit, restart, and list records to prove persistence. Open `models.py` and `database.py` to explain the classes and SQL.

If you returned the sample overdue loan during an earlier practice session, the sample script will not reopen it. Prepare a separate clean practice copy of the project without copying its database when you need a fresh sample workflow.

Be ready to answer: What is a class versus an object? Why use foreign keys? Why use parameters? What happens if a checkout fails halfway? How is overdue calculated? Why preserve history instead of deleting records?

## Rubric and submission checklist

| Criterion | Evidence in this project / action required |
| --- | --- |
| OOP (20) | Three domain classes, meaningful methods, and object collaboration |
| SQLite (25) | Automatic normalised schema, CRUD/status changes, persisted records, three SQL reports |
| Features (20) | All member/equipment/loan menus, searches, and reports |
| Validation (15) | Input checks, business rules, database constraints, friendly messages, tests |
| Live demo (15) | Practise and deliver the walkthrough; explain your code and SQL |
| Submission (5) | Complete the checklist below |

- [ ] Read, understand, and adapt the code in line with your individual-authorship rules.
- [ ] Run the app and tests locally and practise the complete live demo.
- [ ] Configure your own Git name/email and commit the project files.
- [ ] Create a **public** GitHub repository named exactly `Lab_MakerSpace_{GitHubUsername}`. If your username is `Monique237`, use `Lab_MakerSpace_Monique237`.
- [ ] Include source files, README, tests, and sample script. The schema is auto-created; the local database is intentionally ignored by Git.
- [ ] Keep the AI acknowledgement below accurate and attribute any snippets you later adapt.
- [ ] Push the repository and confirm the files are visible publicly.
- [ ] Submit the repository link on Canvas and attend the live demonstration. No video is required.

Technical coverage does not guarantee a mark: the demonstration, understanding, authorship requirements, and submission are assessed too.

## AI assistance acknowledgement

OpenAI Codex assisted with interpreting the assessment, designing the classes and schema, generating application code and tests, checking behaviour, and drafting documentation. This acknowledgement describes the assistance provided; it does not claim that the student has already reviewed or independently written the generated code. Before submission, the student must review, understand, and adapt the work in accordance with the assessment's individual-authorship rules and be able to explain it during the live demonstration.
