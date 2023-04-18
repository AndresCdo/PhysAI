import arxiv
import os

class DataCollector:
    """A class to collect public documents from the ArXiv website."""

    def __init__(self, output_dir='data'):
        """
        Initialize the DataCollector with the output directory.

        Args:
            output_dir: The output directory for the collected documents (default: 'data').
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def collect_documents(self, search_query, max_results=100, sort_by='relevance', sort_order='descending'):
        """
        Collect documents from the ArXiv website based on a search query.

        Args:
            search_query: The search query for collecting documents.
            max_results: The maximum number of documents to collect (default: 100).
            sort_by: The sorting criteria (default: 'relevance').
            sort_order: The sorting order (default: 'descending').
        """
        results = arxiv.query(
            query=search_query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order
        )

        for result in results:
            paper_id = result.get('id').split('/')[-1]
            pdf_url = result.get('pdf_url')
            file_name = f"{paper_id}.pdf"
            output_path = os.path.join(self.output_dir, file_name)

            arxiv.download(result, dirpath=self.output_dir, filename=file_name)
            print(f'Downloaded {file_name} to {output_path}')

if __name__ == '__main__':
    data_collector = DataCollector()

    # Define your search query here (e.g., 'quantum mechanics AND general relativity')
    search_query = 'quantum mechanics AND general relativity'

    data_collector.collect_documents(search_query, max_results=100)