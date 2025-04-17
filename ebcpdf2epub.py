#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
import modules.pdf2md as pdf2md
import modules.mark2epub as mark2epub
import torch


def load_metadata_from_csv(csv_path):
    """
    Load metadata from a CSV file into a dictionary where keys are PDF filenames without extension

    Expected CSV format:
    id,title,authors,language,publisher,publication_date
    """
    metadata = {}
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Document ID' in row:
                    # Use the ID field as the key
                    metadata[row['Document ID']] = row
    except Exception as e:
        print(f"Error loading metadata from CSV: {e}")
    return metadata


def main():
    # Load metadata from CSV
    metadata_dict = load_metadata_from_csv('ebcmetadata.csv')
    if not metadata_dict:
        print(f"Warning: No metadata found in ebcmetadata.csv or file could not be read")

    print(f'Loaded metadata for {len(metadata_dict)} titles')

    if torch.cuda.is_available():
        print("CUDA is available. Using GPU for processing.")
    else:
        print("CUDA is not available. Using CPU for processing.")

    parser = argparse.ArgumentParser(
        description='Convert PDF files to EPUB format via Markdown'
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        type=str,
        help='Path to input PDF file or directory (default: ./input/*.pdf)'
    )
    parser.add_argument(
        'output_path',
        nargs='?',
        type=str,
        help='Path to output directory (default: directory named after PDF)'
    )
    parser.add_argument(
        '--batch-multiplier',
        type=int,
        default=2,
        help='Multiplier for batch size (higher uses more memory but processes faster)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of pages to process'
    )
    parser.add_argument(
        '--start-page',
        type=int,
        default=None,
        help='Page number to start from'
    )
    parser.add_argument(
        '--langs',
        type=str,
        default=None,
        help='Comma-separated list of languages in the document'
    )
    parser.add_argument(
        '--skip-epub',
        action='store_true',
        help='Skip EPUB generation, only create markdown'
    )
    parser.add_argument(
        '--skip-md',
        action='store_true',
        help='Skip markdown generation, use existing markdown files'
    )

    args = parser.parse_args()

    # Get input path
    input_path = Path(args.input_path) if args.input_path else pdf2md.get_default_input_dir()

    # Get queue of PDFs to process
    queue = pdf2md.add_pdfs_to_queue(input_path)
    print(f"Found {len(queue)} PDF files to process")

    # Process each PDF
    for pdf_path in queue:
        pdf_id = pdf_path.stem

        print(f"\nProcessing {pdf_path.name}, doc ID {pdf_id}")

        # Get metadata for this PDF
        pdf_metadata = metadata_dict.get(pdf_id, {})
        if not pdf_metadata:
            raise Exception(f"No metadata found for {pdf_id}")

        # Get output directory for this PDF
        if args.output_path:
            output_path = Path(args.output_path)
            markdown_dir = output_path / pdf_path.stem
        else:
            markdown_dir = pdf2md.get_default_output_dir(pdf_path)
            output_path = markdown_dir.parent

        try:
            # Check if markdown directory exists when skipping MD generation
            if args.skip_md:
                if not markdown_dir.exists():
                    print(f"Error: Markdown directory not found: {markdown_dir}")
                    continue
                print(f"Using existing markdown files from: {markdown_dir}")

            # Convert PDF to Markdown unless skipped
            if not args.skip_md:
                print("Converting PDF to Markdown...")
                pdf2md.convert_pdf(
                    str(pdf_path),
                    markdown_dir,
                    args.batch_multiplier,
                    args.max_pages,
                    args.start_page,
                    args.langs,
                )

            # Convert Markdown to EPUB unless skipped
            print("Converting Markdown to EPUB...")

            # Prepare metadata for EPUB conversion if available
            epub_metadata = {
                'title': pdf_metadata['Title'],
                'authors': pdf_metadata['Authors'],
                'language': pdf_metadata['Language Code'].lower(),
                'publisher': pdf_metadata['Publisher'],
                'publication_date': pdf_metadata['PublicationDate'],
                'identifier': pdf_metadata['EIsbn'],
                'rights': 'All rights reserved'
            }

            mark2epub.convert_to_epub(markdown_dir, output_path, epub_metadata)

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {str(e)}")
            continue


if __name__ == '__main__':
    main()
