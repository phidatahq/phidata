import os
import subprocess
import sys

import click
import inquirer

"""
CLI Tool: Cookbook runner

This tool allows users to interactively navigate through directories, select a target directory, 
and execute all `.py` files in the selected directory. It also tracks cookbooks that fail to execute 
and prompts the user to rerun all failed cookbooks until all succeed or the user decides to exit.

Usage:
    1. Run the tool from the command line:
        python cookbook/scripts/cookbook_runner.py [base_directory]
    
    2. Navigate through the directory structure using the interactive prompts:
        - Select a directory to drill down or choose the current directory.
        - The default starting directory is the current working directory (".").
    
    3. The tool runs all `.py` files in the selected directory and logs any that fail.
    
    4. If any cookbook fails, the tool prompts the user to rerun all failed cookbooks:
        - Select "yes" to rerun all failed cookbooks.
        - Select "no" to exit, and the tool will log remaining failures.

Dependencies:
    - click
    - inquirer

Example:
    $ python cookbook/scripts/cookbook_runner.py cookbook
    Current directory: /cookbook
    > [Select this directory]
    > folder1
    > folder2
    > [Go back]

    Running script1.py...
    Running script2.py...

    --- Error Log ---
    Script: failing_cookbook.py failed to execute.

    Some cookbooks failed. Do you want to rerun all failed cookbooks? [y/N]: y
"""


def select_directory(base_directory):
    while True:
        # Get all subdirectories and files in the current directory
        items = [
            item
            for item in os.listdir(base_directory)
            if os.path.isdir(os.path.join(base_directory, item))
        ]
        items.sort()
        # Add options to select the current directory or go back
        items.insert(0, "[Select this directory]")
        if base_directory != "/":
            items.insert(1, "[Go back]")

        # Prompt the user to select an option
        questions = [
            inquirer.List(
                "selected_item",
                message=f"Current directory: {base_directory}",
                choices=items,
            )
        ]
        answers = inquirer.prompt(questions)

        if not answers or "selected_item" not in answers:
            print("No selection made. Exiting.")
            return None

        selected_item = answers["selected_item"]

        # Handle the user's choice
        if selected_item == "[Select this directory]":
            return base_directory
        elif selected_item == "[Go back]":
            base_directory = os.path.dirname(base_directory)
        else:
            # Drill down into the selected directory
            base_directory = os.path.join(base_directory, selected_item)


def run_python_script(script_path):
    """
    Run a Python script and display its output in real time.
    """
    print(f"Running {script_path}...\n")
    try:
        with subprocess.Popen(
            ["python", script_path],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
        ) as process:
            process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, script_path)

        return True  # Script ran successfully

    except Exception as e:
        print(f"Error while running {script_path}: {e}")
        return False  # Script failed


@click.command()
@click.argument(
    "base_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
def drill_and_run_scripts(base_directory):
    """
    A CLI tool that lets the user drill down into directories and runs all .py files in the selected directory.
    Tracks cookbooks that encounter errors and keeps prompting to rerun until user decides to exit.
    """
    selected_directory = select_directory(base_directory)

    if not selected_directory:
        print("No directory selected. Exiting.")
        return

    print(f"\nRunning .py files in directory: {selected_directory}\n")

    python_files = [
        filename
        for filename in os.listdir(selected_directory)
        if filename.endswith(".py")
        and os.path.isfile(os.path.join(selected_directory, filename))
    ]

    if not python_files:
        print("No .py files found in the selected directory.")
        return

    error_log = []

    # Run each .py file and capture its status
    for py_file in python_files:
        file_path = os.path.join(selected_directory, py_file)
        if not run_python_script(file_path):
            error_log.append(py_file)

    # Log errors and handle rerun logic
    while error_log:
        print("\n--- Error Log ---")
        for py_file in error_log:
            print(f"Cookbook: {py_file} failed to execute.\n")

        # Prompt the user to rerun all failed scripts
        questions = [
            inquirer.Confirm(
                "rerun_failed",
                message="Some cookbooks failed. Do you want to rerun all failed cookbooks?",
                default=False,
            )
        ]
        answers = inquirer.prompt(questions)

        if not answers or not answers.get("rerun_failed"):
            print("\nExiting. Some cookbooks were not successfully executed:")
            for py_file in error_log:
                print(f" - {py_file}")
            return

        print("\nRe-running failed cookbooks...\n")
        new_error_log = []
        for py_file in error_log:
            file_path = os.path.join(selected_directory, py_file)
            if not run_python_script(file_path):
                new_error_log.append(py_file)

        error_log = new_error_log

    print("\nAll cookbooks executed successfully!")


if __name__ == "__main__":
    drill_and_run_scripts()