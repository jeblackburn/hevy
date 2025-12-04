#!/usr/bin/env python3
"""
Script to create folders in Hevy for workout PDFs.

This script:
1. Scans the Workouts directory for PDF files
2. Creates a parent folder for each PDF
3. Creates Week 1-4 subfolders under each parent folder
4. Saves the folder structure and IDs to a JSON file
"""

import json
import os

import backoff
import requests
from pathlib import Path
from typing import Dict, List, Optional


class HevyFolderManager:
    """Manage folder creation in Hevy API."""

    BASE_URL = "https://api.hevyapp.com/v1"

    def __init__(self, api_key: str, output_file):
        """Initialize with API key.

        Args:
            api_key: Hevy API key for authentication
        """
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        self.output_file = output_file

    @backoff.on_exception(backoff.constant, requests.exceptions.RequestException)
    def create_folder(self, title: str) -> Dict:
        """Create a folder in Hevy.

        Args:
            title: Name of the folder
            parent_id: Optional parent folder ID for nested folders

        Returns:
            Dict containing folder information including ID

        Raises:
            requests.HTTPError: If the API request fails
        """
        print("Trying to create folder", title)
        url = f"{self.BASE_URL}/routine_folders"
        try:
            payload = {
                "routine_folder": {
                    "title": title
                }
            }

            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print("Exception while creating folder {}: {}".format(title, e))

    def get_pdf_files(self, workouts_dir: str = "Workouts") -> List[Path]:
        """Get all PDF files from the Workouts directory.

        Args:
            workouts_dir: Directory containing workout PDFs

        Returns:
            List of Path objects for each PDF file
        """
        workouts_path = Path(workouts_dir)
        if not workouts_path.exists():
            raise FileNotFoundError(f"Workouts directory not found: {workouts_dir}")

        pdf_files = list(workouts_path.glob("*.pdf"))
        return sorted(pdf_files)

    def create_folder_structure(self, workouts_dir: str = "Workouts") -> Dict:
        """Create folder structure for all PDF files.

        For each PDF:
        1. Create a parent folder with the PDF name (minus .pdf extension)
        2. Create Week 1, Week 2, Week 3, Week 4 subfolders

        Args:
            workouts_dir: Directory containing workout PDFs

        Returns:
            Dict mapping PDF names to their folder structure with IDs
        """
        pdf_files = self.get_pdf_files(workouts_dir)
        with open(self.output_file) as of:
            folder_structure = json.load(of)

        for pdf_file in pdf_files:
            pdf_name = pdf_file.stem
            if pdf_name in folder_structure:
                print(f"Skipping PDF/folder {pdf_name} because it looks like it's already been processed.")
                continue
            print(f"\nProcessing: {pdf_name}")
            folder_structure[pdf_name] = {}

            try:
                # Create week subfolders
                for week_num in range(1, 5):
                    week_name = f"Week {week_num}"
                    folder_name = f"{pdf_name} - {week_name}"

                    print(f"    Creating subfolder: {folder_name}")

                    try:
                        week_folder = self.create_folder(folder_name)
                        folder_structure[pdf_name][week_name] = week_folder
                    except requests.HTTPError as e:
                        print(f"    ERROR creating {week_name}: {e}")
                        print(f"    Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")


            except requests.HTTPError as e:
                print(f"  ERROR creating parent folder {pdf_name}: {e}")
                print(f"  Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")

        return folder_structure

    def save_folder_structure(self, folder_structure: Dict, output_file: str = "hevy_folders.json"):
        """Save folder structure to JSON file.

        Args:
            folder_structure: Dict containing folder hierarchy and IDs
            output_file: Path to output JSON file
        """
        with open(output_file, 'w') as f:
            json.dump(folder_structure, f, indent=2)

        print(f"\nFolder structure saved to: {output_file}")


def main():
    """Main entry point."""
    # API key from environment or hardcoded
    api_key = os.getenv("HEVY_API_KEY", "2bbe200e-4435-4964-8ed7-cbb52a9d4491")

    # Initialize manager
    manager = HevyFolderManager(api_key, "hevy_folders.json")

    # Create folder structure
    print("Creating Hevy folder structure...")
    print("=" * 60)

    try:
        folder_structure = manager.create_folder_structure()

        # Save to JSON
        manager.save_folder_structure(folder_structure)

        print("\n" + "=" * 60)
        print("Folder creation complete!")
        print(f"Created {len(folder_structure)} parent folders with week subfolders")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
