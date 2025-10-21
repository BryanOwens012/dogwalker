"""Test Aider integration on a sample repository."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add worker module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "worker" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "shared" / "src"))

from config import Config
from dog import Dog

print("Testing Aider integration...")
print()

# Check API key is set
config = Config()
if not config.anthropic_api_key:
    print("❌ ANTHROPIC_API_KEY not set in .env")
    print("Please add your API key to .env file")
    sys.exit(1)

print("✅ ANTHROPIC_API_KEY found")
print()

# Create a temporary test repository
test_dir = Path(tempfile.mkdtemp(prefix="dogwalker-test-"))
print(f"Created test directory: {test_dir}")

try:
    # Initialize a git repo
    os.system(f"cd {test_dir} && git init")
    os.system(f"cd {test_dir} && git config user.name 'Test Dog'")
    os.system(f"cd {test_dir} && git config user.email 'test@dogwalker.dev'")

    # Create a simple Python file
    test_file = test_dir / "hello.py"
    test_file.write_text('print("Hello, world!")\n')

    # Initial commit
    os.system(f"cd {test_dir} && git add . && git commit -m 'Initial commit'")

    print("✅ Created test repository")
    print()

    # Test Aider
    print("Running Aider with test task...")
    print("Task: 'Add a function that returns the sum of two numbers'")
    print()

    dog = Dog(repo_path=test_dir)

    success = dog.run_task("Add a function called add_numbers that takes two numbers and returns their sum. Put it in hello.py.")

    if success:
        print()
        print("✅ Aider task completed successfully!")
        print()
        print("Modified files:")
        print(test_file.read_text())
    else:
        print()
        print("❌ Aider did not make any changes")
        print("This might indicate an issue with the API key or Aider configuration")

    dog.cleanup()

except Exception as e:
    print()
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print()
        print(f"Cleaned up test directory: {test_dir}")

print()
print("✅ Aider integration test complete!")
print()
print("Next steps:")
print("  1. Test full workflow with a real repository")
print("  2. Set up Slack bot and test end-to-end")
