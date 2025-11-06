"""Module for knowledge graph management."""
import json


class KnowledgeGraph:
    """A class to represent a knowledge graph."""

    def __init__(self):
        """Initialise the knowledge graph."""
        self.equations = {}
        self.algorithms = {}
        self.theoretical_principles = {}
        self.definitions = {}
        self.terms = {}
        self.abbreviations = {}

    def add_entry_to_knowledge_graph(self, identifier, data_type, content):
        """Add an entry to the knowledge graph.

        Args:
            identifier (str): The unique identifier of the entry.
            data_type (str): The type of data being added.
            content (str): The content of the entry.
        """

        if (
            identifier in self.__dict__[data_type]
        ):  # Check if the identifier already exists
            print(f"{identifier} already exists")
        else:  # If it doesn't, add it
            self.__dict__[data_type][identifier] = content
            with open(f"{data_type}.json", "w", encoding='utf-8') as f:
                json.dump(self.__dict__[data_type], f, indent=2)

    def get_entry(self, identifier, data_type):
        """
        Retrieve an entry from the knowledge graph.

        Args:
            identifier (str): The unique identifier of the entry.
            data_type (str): The type of data being retrieved.

        Returns:
            The content of the entry, or None if the identifier does not exist.
        """
        return self.__dict__[data_type].get(identifier)

    def update_entry(self, identifier, data_type, content):
        """
        Update an entry in the knowledge graph.

        Args:
            identifier (str): The unique identifier of the entry.
            data_type (str): The type of data being updated.
            content (str): The updated content of the entry.
        """
        if identifier in self.__dict__[data_type]:  # Check if the identifier exists
            self.__dict__[data_type][identifier] = content
            with open(f"{data_type}.json", "w", encoding='utf-8') as f:
                json.dump(self.__dict__[data_type], f, indent=2)
        else:
            print(f"{identifier} does not exist")
