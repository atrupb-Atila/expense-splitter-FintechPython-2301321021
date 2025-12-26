"""
Data models for the Expense Splitter application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class SplitMethod(Enum):
    """Supported methods for splitting expenses."""
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    SHARES = "shares"
    CUSTOM = "custom"


@dataclass
class Participant:
    """Represents a person in an expense group."""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    email: Optional[str] = None

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Participant):
            return self.id == other.id
        return False


@dataclass
class ExpenseSplit:
    """Represents how much a participant owes for an expense."""
    participant_id: str
    amount: float
    percentage: Optional[float] = None
    shares: Optional[int] = None


@dataclass
class Expense:
    """Represents a single expense in a group."""
    description: str
    total_amount: float
    paid_by: str  # participant_id
    currency: str = "BGN"
    split_method: SplitMethod = SplitMethod.EQUAL
    splits: list[ExpenseSplit] = field(default_factory=list)
    date: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    is_recurring: bool = False
    category: Optional[str] = None


@dataclass
class Settlement:
    """Represents a payment from one participant to another."""
    from_participant: str
    to_participant: str
    amount: float
    currency: str = "BGN"


@dataclass
class Group:
    """Represents a group of people sharing expenses."""
    name: str
    participants: list[Participant] = field(default_factory=list)
    expenses: list[Expense] = field(default_factory=list)
    base_currency: str = "BGN"
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)

    def add_participant(self, name: str, email: Optional[str] = None) -> Participant:
        """Add a new participant to the group."""
        participant = Participant(name=name, email=email)
        self.participants.append(participant)
        return participant

    def get_participant_by_id(self, participant_id: str) -> Optional[Participant]:
        """Find a participant by their ID."""
        for p in self.participants:
            if p.id == participant_id:
                return p
        return None

    def get_participant_by_name(self, name: str) -> Optional[Participant]:
        """Find a participant by their name (case-insensitive)."""
        for p in self.participants:
            if p.name.lower() == name.lower():
                return p
        return None
