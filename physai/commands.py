"""
commands.py

A module to provide the main CLI entry point for PhysAI.
"""

import sys


def main():
    """
    Main entry point for the PhysAI command-line interface.
    """
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "version":
            print("PhysAI v0.0.1")
        elif command == "help":
            print("PhysAI - AI-driven platform for physical equations")
            print("\nAvailable commands:")
            print("  version - Show version information")
            print("  help    - Show this help message")
        else:
            print(f"Unknown command: {command}")
            print("Run 'physai help' for available commands")
    else:
        print("PhysAI - AI-driven platform for physical equations")
        print("Run 'physai help' for available commands")


if __name__ == "__main__":
    main()
