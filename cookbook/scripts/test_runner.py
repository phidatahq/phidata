import pytest
import glob
import subprocess
import os

def get_scripts(folder_path):
    """Retrieve all Python script files in the given folder."""
    if not os.path.isdir(folder_path):
        raise ValueError(f"Invalid folder path: {folder_path}")
    return glob.glob(os.path.join(folder_path, "*.py"))

# Get the folder path from the environment variable or default to the current directory
folder_path = os.environ.get("FOLDER_PATH", ".")
scripts = get_scripts(folder_path)

@pytest.mark.parametrize("script", scripts)
def test_script_runs(script):
    print(f"\nRunning: {script}")

    # Run the script and capture its output
    result = subprocess.run(
        ["python", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Check for specific error markers in stdout or stderr
    error_keywords = ["ERROR", "Traceback"]
    if any(keyword in result.stderr for keyword in error_keywords) or any(keyword in result.stdout for keyword in error_keywords):
        pytest.fail(f"Script {script} failed with error:\n{result.stderr.strip()}")

    # Fail the test if the script exits with a non-zero exit code
    assert result.returncode == 0, f"Script {script} failed with exit code {result.returncode}. Error: {result.stderr.strip()}"