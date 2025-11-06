"""Module for preprocessing collected documents."""
import os
import PyPDF2


class DataPreprocessor:
    """A class to preprocess the collected documents."""

    def __init__(self, input_dir='data', output_dir='preprocessed_data'):
        """
        Initialize the DataPreprocessor with input and output directories.

        Args:
            input_dir: The input directory containing the collected documents
                (default: 'data').
            output_dir: The output directory for the preprocessed documents
                (default: 'preprocessed_data').
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF document.

        Args:
            pdf_path: The path to the PDF document.

        Returns:
            text: The extracted text from the PDF document.
        """
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''

            for page in pdf_reader.pages:
                text += page.extract_text()

        return text

    def preprocess_documents(self):
        """
        Preprocess the collected documents by extracting text from the PDF files.
        """
        for file_name in os.listdir(self.input_dir):
            if file_name.endswith('.pdf'):
                input_path = os.path.join(self.input_dir, file_name)
                output_path = os.path.join(self.output_dir, file_name.replace('.pdf', '.txt'))

                text = self.extract_text_from_pdf(input_path)

                with open(output_path, 'w', encoding='utf-8') as file:
                    file.write(text)

                print(f'Preprocessed {file_name} and saved as {output_path}')

if __name__ == '__main__':
    data_preprocessor = DataPreprocessor()

    data_preprocessor.preprocess_documents()
