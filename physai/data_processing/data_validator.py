import os

class DataValidator:
    """A class to validate the preprocessed documents."""

    def __init__(self, input_dir='preprocessed_data', output_dir='validated_data'):
        """
        Initialize the DataValidator with input and output directories.

        Args:
            input_dir: The input directory containing the preprocessed documents (default: 'preprocessed_data').
            output_dir: The output directory for the validated documents (default: 'validated_data').
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def is_relevant(self, text):
        """
        Check if the text is relevant based on certain criteria.

        Args:
            text: The extracted text from the document.

        Returns:
            True if the text is relevant, otherwise False.
        """
        # Define your relevance criteria here (e.g., the presence of certain keywords)
        keywords = ['quantum mechanics', 'general relativity']

        return any(keyword in text.lower() for keyword in keywords)

    def validate_documents(self):
        """
        Validate the preprocessed documents based on the relevance criteria.
        """
        for file_name in os.listdir(self.input_dir):
            if file_name.endswith('.txt'):
                input_path = os.path.join(self.input_dir, file_name)
                output_path = os.path.join(self.output_dir, file_name)

                with open(input_path, 'r', encoding='utf-8') as file:
                    text = file.read()

                if self.is_relevant(text):
                    with open(output_path, 'w', encoding='utf-8') as file:
                        file.write(text)

                    print(f'Validated {file_name} and saved as {output_path}')
                else:
                    print(f'{file_name} did not pass the validation')

if __name__ == '__main__':
    data_validator = DataValidator()

    data_validator.validate_documents()
