import os
import argparse
import pathspec

# Directories to avoid (only print their names)
AVOID_DIRS = {"data", "exports", "test_files_hardmode", "models", "build", "css", "img", "plugins", 'alembic'}


def load_gitignore(root_dir: str) -> pathspec.PathSpec:
    """
    Load and parse the .gitignore file in the root directory.

    Args:
        root_dir (str): The root directory containing .gitignore.

    Returns:
        pathspec.PathSpec: Compiled path specification for ignored files.
    """
    gitignore_path = os.path.join(root_dir, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            lines = f.readlines()
        spec = pathspec.PathSpec.from_lines('gitwildmatch', lines)
        return spec
    return pathspec.PathSpec.from_lines('gitwildmatch', [])


def print_directory_tree(root_dir: str, spec: pathspec.PathSpec, prefix: str = "") -> None:
    """
    Recursively prints the directory structure starting from root_dir, respecting .gitignore.

    Args:
        root_dir (str): The root directory to start printing from.
        spec (pathspec.PathSpec): PathSpec object to match ignored files.
        prefix (str): Prefix for the current level (used for tree structure).
    """
    entries = sorted(os.listdir(root_dir))
    entries = [e for e in entries if not e.startswith('.')]
    entries = [e for e in entries if not spec.match_file(os.path.relpath(os.path.join(root_dir, e)))]

    entries_count = len(entries)
    for idx, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        connector = "└─ " if idx == entries_count - 1 else "├─ "
        print(f"{prefix}{connector}{entry}")

        if os.path.isdir(path):
            if entry in AVOID_DIRS:
                # Do not recurse into these directories
                continue
            extension = "    " if idx == entries_count - 1 else "│   "
            print_directory_tree(path, spec, prefix + extension)


def main():
    """
    Main function to parse arguments, load .gitignore, and initiate tree printing.
    """
    parser = argparse.ArgumentParser(description="Print the structure of a project directory respecting .gitignore and avoiding certain directories.")
    parser.add_argument(
        "directory",
        type=str,
        nargs="?",
        default=".",
        help="Path to the root directory (default: current directory)"
    )
    args = parser.parse_args()

    root_directory = os.path.abspath(args.directory)
    print(root_directory)

    spec = load_gitignore(root_directory)
    print_directory_tree(root_directory, spec)


if __name__ == "__main__":
    main()