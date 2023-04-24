import arxiv
import os
import tarfile
import re
import shutil

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
            arxiv_id = result.get('arxiv_url').split('/')[-1]
            source_url = f'http://arxiv.org/e-print/{arxiv_id}'
            file_name = f"{paper_id}.tar.gz"
            output_path = os.path.join(self.output_dir, file_name)

            arxiv.download(result, src=True, dirpath=self.output_dir, filename=file_name)
            print(f'Downloaded {file_name} to {output_path}')

            with tarfile.open(output_path, 'r:gz') as tar:
                members = [m for m in tar.getmembers() if re.search(r'\.tex$', m.name)]

                if members:
                    tar.extractall(path=self.output_dir, members=members)
                    for member in members:
                        shutil.move(os.path.join(self.output_dir, member.name), os.path.join(self.output_dir, f"{paper_id}-{member.name}"))
                        print(f"Extracted {paper_id}-{member.name} from {file_name}")

                os.remove(output_path)

if __name__ == '__main__':
    data_collector = DataCollector()

    # Define your search query here (e.g., 'quantum mechanics AND general relativity')
    search_query = 'quantum mechanics AND general relativity'

    data_collector.collect_documents(search_query, max_results=100)