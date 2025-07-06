from abc import ABC, abstractmethod


class Command(ABC):
    """Base class for all CLI commands"""

    @abstractmethod
    def add_arguments(self, parser):
        """Add command-specific arguments to parser"""
        pass

    @abstractmethod
    def execute(self, args):
        """Execute the command with given arguments"""
        pass