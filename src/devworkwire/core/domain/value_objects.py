from dataclasses import dataclass

@dataclass(frozen=True)
class IssueId:
    key: str

    def __post_init__(self):
        if not self.key or not self.key.strip():
            raise ValueError("IssueId key cannot be empty")

@dataclass(frozen=True)
class Priority:
    name: str
    
    @classmethod
    def from_jira_name(cls, name: str) -> "Priority":
        return cls(name=name)

@dataclass(frozen=True)
class StoryPoints:
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("StoryPoints cannot be negative")

@dataclass(frozen=True)
class Label:
    name: str

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Label name cannot be empty")
        if " " in self.name:
            raise ValueError("Label name cannot contain spaces")
