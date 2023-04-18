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

        if identifier in self.__dict__[data_type]: # Check if the identifier already exists
            print(f'{identifier} already exists')
        else: # If it doesn't, add it
            self.__dict__[data_type][identifier] = content
            with open(f"{data_type}.json", "w") as f:
                json.dump(self.__dict__[data_type], f, indent=2)
    
