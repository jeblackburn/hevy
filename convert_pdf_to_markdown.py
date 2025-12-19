"""
Convert PDF to Markdown format, preserving text and structure.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF


def pdf_to_markdown(pdf_path: str, output_path: str):
    """
    Convert a PDF file to Markdown format.

    Args:
        pdf_path: Path to the input PDF file
        output_path: Path to save the output Markdown file
    """
    doc = fitz.open(pdf_path)
    markdown_content = []

    for page_num, page in enumerate(doc, start=1):
        # Extract text blocks with their properties
        blocks = page.get_text("dict")["blocks"]

        page_text = []
        for block in blocks:
            # Skip image blocks
            if block["type"] == 1:  # 1 = image block
                continue

            # Process text blocks
            if block["type"] == 0:  # 0 = text block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if text:
                            # Check if text looks like a heading (larger font size)
                            font_size = span["size"]
                            flags = span["flags"]

                            # Bold text (flag & 16)
                            if flags & 16:
                                text = f"**{text}**"

                            # Italic text (flag & 2)
                            if flags & 2:
                                text = f"*{text}*"

                            line_text += text + " "

                    if line_text.strip():
                        page_text.append(line_text.strip())

        # Add page content to markdown
        if page_text:
            markdown_content.extend(page_text)
            markdown_content.append("")  # Empty line between sections

    doc.close()

    # Write to output file
    output = "\n".join(markdown_content)
    Path(output_path).write_text(output, encoding="utf-8")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_pdf_to_markdown.py <input_pdf> <output_md>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_md = sys.argv[2]

    if not Path(input_pdf).exists():
        print(f"Error: Input file '{input_pdf}' not found")
        sys.exit(1)

    print(f"Converting {input_pdf} to Markdown...")
    result_path = pdf_to_markdown(input_pdf, output_md)
    print(f"✓ Conversion complete! Saved to: {result_path}")