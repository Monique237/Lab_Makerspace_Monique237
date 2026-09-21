"""Run with: python main.py"""
import sqlite3
from datetime import date

from database import Database, positive_id


def menu_choice(title, options, exit_label='Back'):
    print(f'\n--- {title} ---')
    for number, label in enumerate(options, start=1):
        print(f'{number}. {label}')
    print(f'0. {exit_label}')
    choice = input('Choose: ').strip()
    if choice not in [str(number) for number in range(len(options) + 1)]:
        raise ValueError('Invalid menu option. Choose one of the numbers shown.')
    return choice


def read_id(prompt):
    return positive_id(input(prompt).strip())


def read_date(prompt):
    value = input(prompt).strip()
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError('Enter a real date in YYYY-MM-DD format.') from None
    if value != parsed.isoformat():
        raise ValueError('Use YYYY-MM-DD format, for example 2026-10-05.')
    return parsed


def show_error(error):
    if isinstance(error, sqlite3.Error):
        print(f'Error: Could not save or read the database ({error}). Check file access and try again.')
    else:
        print(f'Error: {error}')


def show_members(members):
    if not members:
        print('No records found.')
    for member in members:
        status = 'active' if member.active else 'inactive'
        print(f'{member.id} | {member.name} | {member.email} | {status}')


def show_equipment(items):
    if not items:
        print('No records found.')
    for item in items:
        print(f'{item.id} | {item.name} | {item.category} | {item.status}')


def show_loans(loans):
    if not loans:
        print('No records found.')
    for loan in loans:
        if loan.returned_date:
            status = f'returned {loan.returned_date}'
        else:
            status = 'OVERDUE' if loan.is_overdue() else 'open'
        print(f'Loan {loan.id} | member {loan.member_id} | equipment {loan.equipment_id}'
              f' | checkout {loan.checkout_date} | due {loan.due_date} | {status}')


def show_report(rows):
    if not rows:
        print('No records found.')
    for row in rows:
        returned = row['returned_date'] or 'not returned'
        print(f"Loan {row['loan_id']} | {row['member_name']} | {row['equipment_name']}"
              f" | checkout {row['checkout_date']} | due {row['due_date']} | {returned}")


def members_menu(db):
    while True:
        try:
            choice = menu_choice('Members', ['Register', 'List', 'Update', 'Deactivate', 'Reactivate'])
            if choice == '0':
                return
            if choice == '1':
                member = db.add_member(input('Name: '), input('Email: '))
                print(f'Member registered. ID: {member.id}')
            elif choice == '2':
                show_members(db.list_members())
            elif choice == '3':
                member = db.get_member(read_id('Member ID: '))
                print('Leave a field blank to keep its current value.')
                name = input(f'Name [{member.name}]: ').strip() or member.name
                email = input(f'Email [{member.email}]: ').strip() or member.email
                db.update_member(member.id, name, email)
                print('Member updated.')
            else:
                db.set_member_active(read_id('Member ID: '), choice == '5')
                print('Member reactivated.' if choice == '5' else 'Member deactivated.')
        except (ValueError, sqlite3.Error) as error:
            show_error(error)


def equipment_menu(db):
    while True:
        try:
            choice = menu_choice('Equipment', ['Register', 'List', 'Update details', 'Change status'])
            if choice == '0':
                return
            if choice == '1':
                item = db.add_equipment(input('Equipment name: '), input('Category: '))
                print(f'Equipment registered. ID: {item.id}')
            elif choice == '2':
                show_equipment(db.list_equipment())
            elif choice == '3':
                item = db.get_equipment(read_id('Equipment ID: '))
                print('Leave a field blank to keep its current value.')
                name = input(f'Name [{item.name}]: ').strip() or item.name
                category = input(f'Category [{item.category}]: ').strip() or item.category
                db.update_equipment(item.id, name, category)
                print('Equipment updated.')
            elif choice == '4':
                id = read_id('Equipment ID: ')
                status = input('Status (available / maintenance / retired): ').strip().lower()
                db.set_equipment_status(id, status)
                print('Equipment status updated.')
        except (ValueError, sqlite3.Error) as error:
            show_error(error)


def loans_menu(db):
    while True:
        try:
            choice = menu_choice('Loans', ['Checkout equipment', 'Return a loan', 'List loans'])
            if choice == '0':
                return
            if choice == '1':
                member_id = read_id('Member ID: ')
                equipment_id = read_id('Equipment ID: ')
                due_date = read_date('Due date (YYYY-MM-DD): ')
                loan = db.checkout(member_id, equipment_id, due_date)
                print(f'Checkout successful. Loan ID: {loan.id}')
            elif choice == '2':
                db.return_loan(read_id('Loan ID: '))
                print('Loan returned. Equipment is available again.')
            elif choice == '3':
                show_loans(db.list_loans())
        except (ValueError, sqlite3.Error) as error:
            show_error(error)


def search_menu(db):
    while True:
        try:
            choice = menu_choice('Search', ['Member by name', 'Member by ID',
                                            'Equipment by name', 'Equipment by ID'])
            if choice == '0':
                return
            by_id = choice in ('2', '4')
            term = input('ID: ' if by_id else 'Name or part of name: ').strip()
            if choice in ('1', '2'):
                show_members(db.search_members(term, by_id))
            else:
                show_equipment(db.search_equipment(term, by_id))
        except (ValueError, sqlite3.Error) as error:
            show_error(error)


def reports_menu(db):
    while True:
        try:
            choice = menu_choice('Reports', ['Currently borrowed', 'Overdue loans', 'Member loan history'])
            if choice == '0':
                return
            if choice == '1':
                show_report(db.borrowed_report())
            elif choice == '2':
                show_report(db.overdue_report())
            elif choice == '3':
                show_report(db.member_history(read_id('Member ID: ')))
        except (ValueError, sqlite3.Error) as error:
            show_error(error)


def run(db=None):
    """Use an existing database, or open and close the default database."""
    owns_database = db is None
    if owns_database:
        db = Database()
    print('Campus MakerSpace Checkout System')
    try:
        while True:
            try:
                choice = menu_choice('Main menu', ['Members', 'Equipment', 'Loans', 'Search', 'Reports'], 'Exit')
                if choice == '0':
                    break
                if choice == '1':
                    members_menu(db)
                elif choice == '2':
                    equipment_menu(db)
                elif choice == '3':
                    loans_menu(db)
                elif choice == '4':
                    search_menu(db)
                elif choice == '5':
                    reports_menu(db)
            except (ValueError, sqlite3.Error) as error:
                show_error(error)
    except (EOFError, KeyboardInterrupt):
        print('\nInput ended.')
    finally:
        if owns_database:
            db.close()
    print('Goodbye. Saved records will be here next time.')


def main():
    try:
        run()
    except sqlite3.Error as error:
        print(f'Unable to open or initialise the database: {error}')
        print('Check that the project folder is writable and the database file is valid.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
