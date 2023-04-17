class KnowledgeGraph:
    def __init__(self):
        self.equations = {}
        self.algorithms = {}
        self.theoretical_principles = {}
    def add_entry_to_knowledge_graph(self, identifier, data_type, content):
        if identifier in self.__dict__[data_type]:
            print(f'{identifier} already exists')
        else:
            self.__dict__[data_type][identifier] = content
            with open(f"{data_type}.txt", "a") as f:
                f.write(f"% {identifier}% {content}\n")
