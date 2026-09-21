# Campus MakerSpace Checkout System — design

## Purpose and scope

Build a small Python terminal application for a makerspace operator to manage members, equipment, and borrowing. Use Python's standard library and SQLite, with no installation of third-party packages. Keep the code readable for a first-year student to explain in a live demonstration. Cover every technical requirement in the supplied assessment; the grade also depends on the student's understanding, demonstration, and submission.

## Files and responsibilities

- `main.py`: entry point, numbered menus, input conversion, output formatting, and friendly error messages.
- `models.py`: Member, Equipment, and Loan classes with attributes and behaviour.
- `database.py`: Database class owning connection lifecycle, schema creation, parameterised SQL, transactions, record mapping, and reports.
- `README.md`: setup/run instructions, class and table explanations, sample data instructions, demo walkthrough, rubric checklist, and accurate AI acknowledgement.
- `seed_demo.py`: optional, repeat-safe sample setup using the application operations and fictional data; never replaces existing records.
- `tests/test_makerspace.py`: standard-library unittest checks using temporary databases.
- `.gitignore`: excludes generated databases, Python caches, and local environment files.

The database is created automatically beside the application, independently of the directory from which the user launches it. Documentation includes `python main.py`, sample setup, and test commands. There is no need for a requirements file when using only the standard library.

## Class design and collaboration

Member has an ID, name, email, and active flag. Its update and deactivate methods enforce valid member details and status changes; its borrowing eligibility method reports whether it is active.

Equipment has an ID, name, category, and status. Status is one of available, borrowed, maintenance, or retired. Methods include is_available, borrow, return_item, and a controlled status update. Operators cannot manually mark equipment as borrowed, or change borrowed equipment's status; borrowing and returning own those transitions.

Loan has an ID, member ID, equipment ID, checkout date, due date, and optional return date. Its creation method uses Member and Equipment objects to check eligibility and availability. Its close method collaborates with Equipment to return an item, and is_overdue compares the due date with today's date for open loans.

Database loads these objects and coordinates persistence. Checkout and return call domain methods and save all related changes in one transaction. This provides meaningful object collaboration without an additional services layer.

## SQLite schema

| Table | Columns and constraints |
| --- | --- |
| members | id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE with case-insensitive comparison, active INTEGER NOT NULL constrained to 0 or 1 |
| equipment | id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, status TEXT NOT NULL constrained to the four supported states |
| loans | id INTEGER PRIMARY KEY, member_id and equipment_id required foreign keys, checkout_date and due_date required ISO dates, returned_date nullable |

Enable foreign keys on every connection. Enforce nonblank text, due_date >= checkout_date, and returned_date >= checkout_date. Validate real calendar dates in Python. A partial unique index on equipment_id for open loans prevents two active loans for one item. Do not duplicate member names or equipment descriptions in loans.

Use parameterised values for all user input. Guard checkout and return inside explicit transactions, rechecking current database state before changes. Roll back both the loan and equipment changes on failure.

## Menus and CRUD

The main menu offers Members, Equipment, Loans, Search, Reports, and Exit. Each submenu has a Back option.

- Members: register, list, update name/email, deactivate, and reactivate. Refuse deactivation while the member has open loans.
- Equipment: register, list, update name/category, and change status between available, maintenance, and retired when not borrowed.
- Loans: checkout, list, and return. Creating a loan requires an active member, available equipment, and a valid due date no earlier than checkout. Return closes an open loan and restores equipment availability.
- Search: choose members or equipment, then exact positive ID or partial name. Treat name input literally, including SQL wildcard characters. Return clear feedback for no matches.
- Reports: currently borrowed equipment, overdue loans, and member loan history. SQL JOIN queries provide member and equipment names and the relevant dates. Order results predictably; show clear empty results.

Deactivation, retirement, and loan closure implement the assessment's permitted status-update alternative to deletion, preserving borrowing history. All operations read the stored data rather than a hard-coded list.

## Validation and feedback

Reject empty required fields, malformed email addresses with a simple documented check, duplicate emails, invalid menu options, nonpositive or nonnumeric IDs, nonexistent records, invalid dates, inactive members, unavailable items, and repeated returns. Strip surrounding whitespace from text. Update prompts may use blank input to preserve an existing value.

Handle expected validation and SQLite errors with actionable messages and keep the menu running where recovery is possible. Handle end-of-input and keyboard interruption cleanly. If the database cannot be opened or initialised, explain the failure and exit cleanly. Do not suppress unexpected programming errors with a blanket exception handler.

An item due today becomes overdue tomorrow. A returned loan never appears in the overdue report. Keep all loan history.

## Sample data and demonstration

The optional sample script adds fictional members and equipment, an open overdue loan, and a returned loan using a documented historical-date parameter on the same business operations. Running it twice does not duplicate the sample records; it does not reset user data.

The README demonstration covers registration, editing, both search modes, checkout, rejected duplicate checkout, all reports, return, rejected repeated return, status changes, and restart persistence. Include short explanations of classes versus objects, foreign keys, JOINs, parameterised SQL, and transactions for practice.

## Acceptance checks mapped to the rubric

| Criterion | Evidence and verification |
| --- | --- |
| OOP — 20 | Three domain classes with meaningful methods; loan creation and return visibly use Member/Equipment objects; explain responsibilities in README. |
| SQLite — 25 | Automatic schema creation, foreign keys, persisted CRUD/status changes, parameterised SQL, three meaningful SQL reports. Verify records after closing and reopening the database. |
| Features — 20 | Exercise every menu and the complete register → checkout → report → return workflow, including search and updates. |
| Validation — 15 | Test missing records, bad IDs/dates, blank inputs, duplicate email, unavailable equipment, repeated returns, active-loan restrictions, and atomic rollback. |
| Live demo — 15 | Provide a reproducible demo walkthrough and explanation prompts; the student must practise and deliver the live demonstration. |
| Submission — 5 | README, source, auto-created schema, sample setup, and acknowledgement; public GitHub repo named Lab_MakerSpace_{GitHubUsername}, Canvas link, and attendance remain explicit submission steps. |

Use temporary SQLite databases for automated tests. Test domain behaviour, SQL reports including due-date boundaries, persistence, and transaction failure consistency. Run a scripted CLI smoke test for prompts and invalid inputs. No network, GUI, accounts, fines, reservations, or unrelated features are in scope.

## Authorship and completion

Explain generated or revised code during implementation and record AI assistance accurately in README. The student must review, understand, and adapt the work consistent with the assessment's individual-authorship requirements. Do not claim the live demo or submission has happened, or promise a mark of 100%.
