import asyncio
import os
import random
from pathlib import Path
from app.infrastructure.loaders.file_processor import FileProcessor
from infrastructure.repositories.repository import FileRepository


class DummyFileRepository(FileRepository):
    """Dummy repo that always returns a fake file record."""

    def __init__(self):
        super().__init__(db=None)  # Pass None to db because we don't need it

    async def get_file_by_path(self, path: str):
        class DummyRecord:
            id = "dummy-file-id"
            owner_id = "dummy-owner-id"
            theme_id = "dummy-theme-id"
        return DummyRecord()


async def create_large_text_file(path: Path, size_kb: int):
    """Create a large text file filled with random words."""
    words = ["apple", "banana", "carrot", "delta", "elephant", "french", "german", "happiness", "internet", "jungle"]
    text = " ".join(random.choices(words, k=(size_kb * 100)))  # Roughly 100 words per KB
    path.write_text(text)


async def create_mixed_language_file(path: Path):
    """Create a file mixing multiple languages."""
    content = (
        "Hello world! Bonjour le monde! Hola mundo! こんにちは世界！안녕하세요 세계! Привет мир! "
        "This is a test document with multiple languages crammed together to confuse detection."
    )
    path.write_text(content, encoding="utf-8")


async def create_corrupted_file(path: Path):
    """Create a corrupted file (non-UTF-8 bytes)."""
    with open(path, "wb") as f:
        f.write(os.urandom(512))  # Random binary garbage


async def create_emoji_spam_file(path: Path):
    """Create a file full of emoji spam and weird characters."""
    emojis = ''.join(random.choices("😀😂🤣😜😎🤖👾🦄🐉🔥💥✨🌟🚀🛸", k=200))
    path.write_text(f"This file contains nonsense emoji spam: {emojis}", encoding="utf-8")


async def create_deep_nested_structure(base_dir: Path, depth: int):
    """Create nested folders and files inside."""
    current = base_dir
    for i in range(depth):
        current = current / f"nested_{i}"
        current.mkdir(parents=True, exist_ok=True)
        # Drop a file at each level
        file_path = current / f"file_at_depth_{i}.txt"
        file_path.write_text(f"This is file at depth {i}. Very profound.")

async def create_test_files(test_dir: Path):
    """Create all types of nasty, heavy, and edge case files."""
    os.makedirs(test_dir, exist_ok=True)

    await create_large_text_file(test_dir / "large_file.txt", size_kb=500)  # 500KB
    await create_mixed_language_file(test_dir / "mixed_language.txt")
    await create_corrupted_file(test_dir / "corrupted.bin")
    await create_emoji_spam_file(test_dir / "emoji_spam.txt")
    await create_deep_nested_structure(test_dir / "deep_structure", depth=10)

    # A few normal files sprinkled in
    (test_dir / "normal_good.txt").write_text("This is a clean normal file.")
    (test_dir / "almost_empty.txt").write_text("A.")

async def main():
    test_directory = Path("./test_files_hardmode")
    await create_test_files(test_directory)

    dummy_repo = DummyFileRepository()
    processor = FileProcessor(file_repository=dummy_repo)

    print("\nProcessing files... This may take a moment...")
    documents, report = await processor.process_directory(str(test_directory))

    print("\n=== Documents Summary ===")
    for doc in documents:
        print(f"ID: {doc.id} | Content snippet: {doc.content[:60]}... | Metadata keys: {list(doc.metadata.keys())}")

    print("\n=== Processing Report ===")
    import pprint
    pprint.pprint(report)

if __name__ == "__main__":
    asyncio.run(main())
