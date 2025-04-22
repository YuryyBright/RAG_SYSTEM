import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import os
import tempfile
from pathlib import Path
import pytest

from app.infrastructure.loaders.file_processor import FileProcessor
from domain.entities import ProcessedFile


class TestFileProcessor(unittest.TestCase):
    def setUp(self):
        # Create a mock repository for testing
        self.mock_file_repo = MagicMock()
        self.mock_file_repo.get_file_by_path = AsyncMock()

        # Initialize the FileProcessor with the mock repository
        self.processor = FileProcessor(self.mock_file_repo)

        # Set up a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create test files with various extensions
        self.create_test_files()

    def tearDown(self):
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def create_test_files(self):
        """Create test files with different extensions and content"""
        # Text file with English content
        with open(self.test_dir / "english.txt", "w", encoding="utf-8") as f:
            f.write("This is a sample English text file for testing language detection.")

        # Markdown file with Spanish content - avoid special characters
        with open(self.test_dir / "spanish.md", "w", encoding="utf-8") as f:
            f.write("Este es un archivo markdown en espanol para probar la deteccion de idioma.")

        # Empty file
        with open(self.test_dir / "empty.txt", "w", encoding="utf-8") as f:
            f.write("")

        # Very short content file
        with open(self.test_dir / "short.txt", "w", encoding="utf-8") as f:
            f.write("Hi")

        # File with unsupported extension
        with open(self.test_dir / "image.jpg", "w", encoding="utf-8") as f:
            f.write("Not really an image but with jpg extension")

        # Create a subfolder with a file
        subdir = self.test_dir / "subdir"
        subdir.mkdir(exist_ok=True)
        with open(subdir / "subfile.txt", "w", encoding="utf-8") as f:
            f.write("This is a file in a subdirectory.")

    @pytest.mark.asyncio
    async def test_process_file_successful(self):
        """Test processing a valid text file with successful language detection"""
        # Mock the reader and cleaner
        with patch('app.infrastructure.loaders.file_processor.ReaderFactory.get_reader') as mock_reader_factory, \
                patch('app.infrastructure.loaders.file_processor.CleanerFactory.get_cleaner') as mock_cleaner_factory, \
                patch('app.infrastructure.loaders.file_processor.detect') as mock_detect:
            # Set up mocks
            mock_reader = MagicMock()
            mock_reader.read.return_value = "This is sample content in English."
            mock_reader_factory.return_value = mock_reader

            mock_cleaner = MagicMock()
            mock_cleaner.clean.return_value = "This is sample content in English."
            mock_cleaner_factory.return_value = mock_cleaner

            # Mock the language detection to return 'en'
            mock_detect.return_value = 'en'

            # Process the file
            file_path = self.test_dir / "english.txt"
            result = await self.processor.process_file(file_path)

            # Verify results
            self.assertTrue(result.is_readable)
            self.assertTrue(result.is_language_detected)
            self.assertEqual(result.language, 'en')
            self.assertEqual(result.content, "This is sample content in English.")
            self.assertEqual(result.filename, "english.txt")

            # Verify metadata
            self.assertEqual(result.metadata["source"], str(file_path))
            self.assertEqual(result.metadata["extension"], ".txt")
            self.assertFalse(result.metadata["has_warnings"])

    @pytest.mark.asyncio
    async def test_process_file_with_unreadable_content(self):
        """Test processing a file that cannot be read properly"""
        # Mock the reader to raise an exception
        with patch('app.infrastructure.loaders.file_processor.ReaderFactory.get_reader') as mock_reader_factory:
            mock_reader = MagicMock()
            mock_reader.read.side_effect = Exception("Failed to read file")
            mock_reader_factory.return_value = mock_reader

            # Process the file
            file_path = self.test_dir / "english.txt"
            result = await self.processor.process_file(file_path)

            # Verify results
            self.assertFalse(result.is_readable)
            self.assertFalse(result.is_language_detected)
            self.assertEqual(result.content, "")
            self.assertEqual(result.metadata["error"], "Failed to read file")
            self.assertTrue(result.metadata["has_warnings"])

    @pytest.mark.asyncio
    async def test_process_file_with_language_detection_failure(self):
        """Test processing a file where language detection fails"""
        # Mock the reader and language detection
        with patch('app.infrastructure.loaders.file_processor.ReaderFactory.get_reader') as mock_reader_factory, \
                patch('app.infrastructure.loaders.file_processor.CleanerFactory.get_cleaner') as mock_cleaner_factory, \
                patch('app.infrastructure.loaders.file_processor.detect') as mock_detect:
            mock_reader = MagicMock()
            mock_reader.read.return_value = "Content that will cause language detection to fail."
            mock_reader_factory.return_value = mock_reader

            mock_cleaner = MagicMock()
            mock_cleaner.clean.return_value = "Content that will cause language detection to fail."
            mock_cleaner_factory.return_value = mock_cleaner

            # Make language detection fail
            from langdetect.lang_detect_exception import LangDetectException
            mock_detect.side_effect = LangDetectException("Language detection failed")

            # Process the file
            file_path = self.test_dir / "problematic.txt"
            result = await self.processor.process_file(file_path)

            # Verify results
            self.assertTrue(result.is_readable)
            self.assertFalse(result.is_language_detected)
            self.assertIsNone(result.language)
            self.assertTrue(result.metadata["has_warnings"])
            self.assertIn("language_error", result.metadata)
            self.assertIn("Language detection failed", result.metadata["language_error"])

    @pytest.mark.asyncio
    async def test_process_file_with_very_short_content(self):
        """Test processing a file with content too short for language detection"""
        # Process the actual short file we created
        file_path = self.test_dir / "short.txt"
        result = await self.processor.process_file(file_path)

        # Verify results
        self.assertTrue(result.is_readable)
        self.assertFalse(result.is_language_detected)
        self.assertIsNone(result.language)
        self.assertTrue(result.metadata["has_warnings"])
        self.assertIn("language_error", result.metadata)
        self.assertIn("Content too short", result.metadata["language_error"])

    @pytest.mark.asyncio
    async def test_process_directory_non_recursive(self):
        """Test processing a directory without recursion"""
        # Set up the mock to return file records
        mock_file_record = MagicMock()
        mock_file_record.id = str(uuid.uuid4())
        mock_file_record.owner_id = str(uuid.uuid4())
        mock_file_record.theme_id = str(uuid.uuid4())
        self.mock_file_repo.get_file_by_path.return_value = mock_file_record

        # Process the directory without recursion
        documents, report = await self.processor.process_directory(str(self.test_dir), recursive=False)

        # Only files in the top directory should be processed (not the one in subdir)
        # Count the number of valid files we created in the top directory
        valid_files_count = len([f for f in os.listdir(self.test_dir)
                                 if Path(self.test_dir / f).is_file() and
                                 Path(f).suffix.lstrip('.') in self.processor.supported_extensions])

        # Verify the correct number of documents were processed
        self.assertEqual(len(documents), valid_files_count,
                         f"Expected {valid_files_count} documents, got {len(documents)}")

        # Check report
        self.assertEqual(report["summary"]["total_files"], valid_files_count)
        self.assertGreaterEqual(report["summary"]["successful"], 0)

    @pytest.mark.asyncio
    async def test_process_directory_recursive(self):
        """Test processing a directory with recursion"""
        # Set up the mock to return file records
        mock_file_record = MagicMock()
        mock_file_record.id = str(uuid.uuid4())
        mock_file_record.owner_id = str(uuid.uuid4())
        mock_file_record.theme_id = str(uuid.uuid4())
        self.mock_file_repo.get_file_by_path.return_value = mock_file_record

        # Process the directory with recursion
        documents, report = await self.processor.process_directory(str(self.test_dir), recursive=True)

        # All valid files should be processed (including the one in subdir)
        # We need to count them manually because the processor skips unsupported extensions
        valid_files_count = 0
        for root, _, files in os.walk(self.test_dir):
            for file in files:
                if Path(file).suffix.lstrip('.') in self.processor.supported_extensions:
                    valid_files_count += 1

        # Verify the correct number of documents were processed
        self.assertEqual(len(documents), valid_files_count)

        # Check report
        self.assertEqual(report["summary"]["total_files"], valid_files_count)

    @pytest.mark.asyncio
    async def test_convert_to_document(self):
        """Test converting a ProcessedFile to a Document"""
        # Create a ProcessedFile
        processed_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="test.txt",
            content="Test content",
            language="en",
            is_readable=True,
            is_language_detected=True,
            metadata={
                "source": str(self.test_dir / "test.txt"),
                "extension": ".txt",
                "file_size": 100
            }
        )

        # Set up mock file repository response
        mock_file_record = MagicMock()
        mock_file_record.id = "file-id-123"
        mock_file_record.owner_id = "owner-id-456"
        mock_file_record.theme_id = "theme-id-789"
        self.mock_file_repo.get_file_by_path.return_value = mock_file_record

        # Convert to document
        document = await self.processor._convert_to_document(processed_file, self.test_dir / "test.txt")

        # Verify document properties
        self.assertIsNotNone(document)
        self.assertEqual(document.id, processed_file.id)
        self.assertEqual(document.content, "Test content")
        self.assertEqual(document.metadata["language"], "en")
        self.assertEqual(document.file_id, "file-id-123")
        self.assertEqual(document.owner_id, "owner-id-456")
        self.assertEqual(document.theme_id, "theme-id-789")

    @pytest.mark.asyncio
    async def test_convert_to_document_with_missing_file_record(self):
        """Test converting a ProcessedFile to a Document when file record not found"""
        # Create a ProcessedFile
        processed_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="nonexistent.txt",
            content="Test content",
            language="en",
            is_readable=True,
            is_language_detected=True,
            metadata={
                "source": str(self.test_dir / "nonexistent.txt"),
                "extension": ".txt",
                "file_size": 100
            }
        )

        # Set up mock file repository to return None (file not found)
        self.mock_file_repo.get_file_by_path.return_value = None

        # Convert to document
        document = await self.processor._convert_to_document(processed_file, self.test_dir / "nonexistent.txt")

        # Verify document is None since file record wasn't found
        self.assertIsNone(document)

    @pytest.mark.asyncio
    async def test_convert_to_document_with_db_error(self):
        """Test converting a ProcessedFile to a Document when DB query fails"""
        # Create a ProcessedFile
        processed_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="problematic.txt",
            content="Test content",
            language="en",
            is_readable=True,
            is_language_detected=True,
            metadata={
                "source": str(self.test_dir / "problematic.txt"),
                "extension": ".txt",
                "file_size": 100
            }
        )

        # Set up mock file repository to raise an exception
        self.mock_file_repo.get_file_by_path.side_effect = Exception("Database error")

        # Convert to document
        document = await self.processor._convert_to_document(processed_file, self.test_dir / "problematic.txt")

        # Verify document is None since an error occurred
        self.assertIsNone(document)

    def test_generate_enhanced_report(self):
        """Test generating the processing report"""
        # Create some sample processed files
        success_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="success.txt",
            content="Successful content",
            language="en",
            is_readable=True,
            is_language_detected=True,
            metadata={"source": "success.txt"}
        )

        unreadable_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="unreadable.txt",
            content="",
            language=None,
            is_readable=False,
            is_language_detected=False,
            metadata={"source": "unreadable.txt", "error": "Failed to read"}
        )

        language_failure_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="lang_failure.txt",
            content="Content with language detection failure",
            language=None,
            is_readable=True,
            is_language_detected=False,
            metadata={"source": "lang_failure.txt", "language_error": "Could not detect language", "has_warnings": True}
        )

        empty_file = ProcessedFile(
            id=str(uuid.uuid4()),
            filename="empty.txt",
            content="",
            language=None,
            is_readable=True,
            is_language_detected=False,
            metadata={"source": "empty.txt"}
        )

        # Populate the processor's lists
        self.processor.successful_files = [success_file]
        self.processor.unreadable_files = [unreadable_file]
        self.processor.language_detection_failures = [language_failure_file]
        self.processor.files_with_warnings = [language_failure_file]

        # Generate the report
        report = self.processor._generate_enhanced_report()

        # Verify report structure and content
        self.assertEqual(report["summary"]["total_files"], 3)  # success + unreadable + warning
        self.assertEqual(report["summary"]["successful"], 1)
        self.assertEqual(report["summary"]["unreadable"], 1)
        self.assertEqual(report["summary"]["language_detection_failures"], 1)
        self.assertEqual(report["summary"]["files_with_warnings"], 1)

        # Check details sections
        self.assertEqual(len(report["details"]["successful_files"]), 1)
        self.assertEqual(len(report["details"]["unreadable_files"]), 1)
        self.assertEqual(len(report["details"]["language_detection_failures"]), 1)

        # Check recommendations
        self.assertIn("lang_failure.txt", report["recommendations"]["files_to_review"])
        self.assertIn("unreadable.txt", report["recommendations"]["files_to_consider_removing"])

    def test_extract_warnings(self):
        """Test extracting warnings from metadata"""
        # Create metadata with various warnings
        metadata = {
            "language_error": "Could not detect language",
            "error": "Processing error occurred",
            "other_info": "This is not a warning"
        }

        warnings = self.processor._extract_warnings(metadata)

        # Verify warnings were correctly extracted
        self.assertEqual(len(warnings), 2)
        self.assertIn("Language detection issue: Could not detect language", warnings)
        self.assertIn("Processing error: Processing error occurred", warnings)


if __name__ == "__main__":
    unittest.main()