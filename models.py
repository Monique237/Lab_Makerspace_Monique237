"""The three real-world objects used by the MakerSpace application."""
from datetime import date


def required_text(value, label):
    value = value.strip()
    if not value:
        raise ValueError(f'{label} cannot be blank.')
    return value


class Member:
    def __init__(self, id, name, email, active=True):
        self.id = id
        self.update(name, email)
        self.active = bool(active)

    def update(self, name, email):
        name = required_text(name, 'Name')
        email = required_text(email, 'Email')
        parts = email.split('@')
        if (len(parts) != 2 or not parts[0] or '.' not in parts[1]
                or any(not part for part in parts[1].split('.'))
                or any(char.isspace() for char in email)):
            raise ValueError('Enter an email such as name@example.com.')
        self.name = name
        self.email = email

    def can_borrow(self):
        return self.active

    def deactivate(self, has_open_loans):
        if has_open_loans:
            raise ValueError('Return this member\'s open loans before deactivating them.')
        self.active = False

    def reactivate(self):
        self.active = True


class Equipment:
    def __init__(self, id, name, category, status='available'):
        self.id = id
        self.update(name, category)
        if status not in ('available', 'borrowed', 'maintenance', 'retired'):
            raise ValueError('Unknown equipment status.')
        self.status = status

    def update(self, name, category):
        name = required_text(name, 'Equipment name')
        category = required_text(category, 'Category')
        self.name = name
        self.category = category

    def is_available(self):
        return self.status == 'available'

    def borrow(self):
        if not self.is_available():
            raise ValueError(f'Equipment is {self.status}; it is not available.')
        self.status = 'borrowed'

    def return_item(self):
        if self.status != 'borrowed':
            raise ValueError('This equipment is not currently borrowed.')
        self.status = 'available'

    def set_status(self, status):
        if self.status == 'borrowed':
            raise ValueError('Return the open loan before changing equipment status.')
        if status not in ('available', 'maintenance', 'retired'):
            raise ValueError('Choose available, maintenance, or retired.')
        self.status = status


class Loan:
    def __init__(self, id, member_id, equipment_id, checkout_date, due_date,
                 returned_date=None):
        if due_date < checkout_date:
            raise ValueError('Due date cannot be before checkout date.')
        if returned_date is not None and returned_date < checkout_date:
            raise ValueError('Return date cannot be before checkout date.')
        self.id = id
        self.member_id = member_id
        self.equipment_id = equipment_id
        self.checkout_date = checkout_date
        self.due_date = due_date
        self.returned_date = returned_date

    @classmethod
    def create(cls, member, equipment, due_date, checkout_date=None):
        checkout_date = checkout_date or date.today()
        if not member.can_borrow():
            raise ValueError('This member is inactive. Reactivate them before checkout.')
        loan = cls(None, member.id, equipment.id, checkout_date, due_date)
        equipment.borrow()
        return loan

    def close(self, equipment, returned_date=None):
        returned_date = returned_date or date.today()
        if self.returned_date is not None:
            raise ValueError('This loan has already been returned.')
        if equipment.id != self.equipment_id:
            raise ValueError('This equipment does not belong to the loan.')
        if returned_date < self.checkout_date:
            raise ValueError('Return date cannot be before checkout date.')
        equipment.return_item()
        self.returned_date = returned_date

    def is_overdue(self, today=None):
        today = today or date.today()
        return self.returned_date is None and self.due_date < today
