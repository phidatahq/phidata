from typing import Optional, List
from pathlib import Path
from phi.tools import Toolkit
from phi.utils.log import logger
import subprocess
import shutil
import json


class WebTools(Toolkit):
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        save_and_run: bool = True,
        npm_install: bool = False,
        run_code: bool = False,
        list_files: bool = False,
        run_files: bool = False,
        read_files: bool = False,
    ):
        super().__init__(name="web_tools")

        self.base_dir: Path = base_dir or Path.cwd()

        if run_code:
            self.register(self.run_web_code, sanitize_arguments=False)
        if save_and_run:
            self.register(self.save_to_file_and_run, sanitize_arguments=False)
        if npm_install:
            self.register(self.npm_install_package)
        if run_files:
            self.register(self.run_web_project)
        if read_files:
            self.register(self.read_file)
        if list_files:
            self.register(self.list_files)

    def save_to_file_and_run(self, file_name: str, code: str, overwrite: bool = True) -> str:
        """This function saves web development code (HTML, CSS, JS) to a file called `file_name` and then serves it.
        If successful, returns a success message.
        If failed, returns an error message.

        Make sure the file_name ends with an appropriate extension (.html, .css, .js)

        :param file_name: The name of the file the code will be saved to.
        :param code: The code to save.
        :param overwrite: Overwrite the file if it already exists.
        :return: Success message if successful, otherwise an error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            logger.debug(f"Saving code to {file_path}")
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists() and not overwrite:
                return f"File {file_name} already exists"
            file_path.write_text(code)
            logger.info(f"Saved: {file_path}")
            return f"Successfully saved code to {str(file_path)}"
        except Exception as e:
            logger.error(f"Error saving code: {e}")
            return f"Error saving code: {e}"

    def run_web_code(self, directory: Optional[str] = None) -> str:
        """This function serves web code in the given directory using a local development server.
        If successful, returns the address of the local server.
        If failed, returns an error message.

        :param directory: The directory to serve. If None, serves the base_dir.
        :return: Address of the local server if successful, otherwise an error message.
        """
        try:
            dir_to_serve = self.base_dir.joinpath(directory) if directory else self.base_dir
            logger.info(f"Serving directory: {dir_to_serve}")
            port = 8000
            cmd = ["python", "-m", "http.server", str(port)]
            self.server_process = subprocess.Popen(cmd, cwd=str(dir_to_serve))
            logger.info(f"Started local server at http://localhost:{port}")
            return f"Serving at http://localhost:{port}"
        except Exception as e:
            logger.error(f"Error running web code: {e}")
            return f"Error running web code: {e}"

    def stop_web_server(self) -> str:
        """Stops the web server if it's running."""
        try:
            if hasattr(self, "server_process") and self.server_process:
                self.server_process.terminate()
                self.server_process.wait()
                logger.info("Stopped web server")
                return "Web server stopped"
            else:
                return "No web server is running"
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
            return f"Error stopping web server: {e}"

    def npm_install_package(self, package_name: str) -> str:
        """Installs an npm package in the current environment.

        :param package_name: The name of the package to install.
        :return: Success message if successful, otherwise an error message.
        """
        try:
            logger.debug(f"Installing npm package {package_name}")
            subprocess.check_call(["npm", "install", package_name], cwd=str(self.base_dir))
            return f"Successfully installed npm package {package_name}"
        except Exception as e:
            logger.error(f"Error installing npm package {package_name}: {e}")
            return f"Error installing npm package {package_name}: {e}"

    def create_new_project(self, framework: str, project_name: str) -> str:
        """Creates a new web project using a specified framework.

        :param framework: The framework to use ('react', 'angular', 'vue', etc.)
        :param project_name: The name of the new project.
        :return: Success message if successful, otherwise an error message.
        """
        try:
            logger.info(f"Creating new {framework} project: {project_name}")
            project_path = self.base_dir.joinpath(project_name)
            if project_path.exists():
                return f"Project {project_name} already exists"
            if framework.lower() == "react":
                subprocess.check_call(["npx", "create-react-app", project_name], cwd=str(self.base_dir))
            elif framework.lower() == "angular":
                subprocess.check_call(["npx", "-p", "@angular/cli", "ng", "new", project_name], cwd=str(self.base_dir))
            elif framework.lower() == "vue":
                subprocess.check_call(["npx", "@vue/cli", "create", project_name], cwd=str(self.base_dir))
            else:
                return f"Unsupported framework: {framework}"
            return f"Successfully created {framework} project: {project_name}"
        except Exception as e:
            logger.error(f"Error creating project {project_name}: {e}")
            return f"Error creating project {project_name}: {e}"

    def run_web_project(self, project_name: str) -> str:
        """Runs the web project using the appropriate development server.

        :param project_name: The name of the project to run.
        :return: Address of the local server if successful, otherwise an error message.
        """
        try:
            project_path = self.base_dir.joinpath(project_name)
            if not project_path.exists():
                return f"Project {project_name} does not exist"
            logger.info(f"Running project {project_name}")
            cmd = ["npm", "start"]
            self.server_process = subprocess.Popen(cmd, cwd=str(project_path))
            logger.info("Started development server")
            return "Development server started"
        except Exception as e:
            logger.error(f"Error running project {project_name}: {e}")
            return f"Error running project {project_name}: {e}"

    def read_file(self, file_name: str) -> str:
        """Reads the contents of the file `file_name` and returns the contents if successful.

        :param file_name: The name of the file to read.
        :return: The contents of the file if successful, otherwise returns an error message.
        """
        try:
            logger.info(f"Reading file: {file_name}")
            file_path = self.base_dir.joinpath(file_name)
            contents = file_path.read_text()
            return str(contents)
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"Error reading file: {e}"

    def list_files(self, directory: Optional[str] = None) -> str:
        """Returns a list of files in the specified directory.

        :param directory: The directory to list files in. If None, uses the base directory.
        :return: Comma separated list of files.
        """
        try:
            dir_to_list = self.base_dir.joinpath(directory) if directory else self.base_dir
            logger.info(f"Listing files in : {dir_to_list}")
            files = [str(file_path.name) for file_path in dir_to_list.iterdir()]
            return ", ".join(files)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return f"Error listing files: {e}"

    def build_project(self, project_name: str) -> str:
        """Builds the web project for production deployment.

        :param project_name: The name of the project to build.
        :return: Success message if successful, otherwise an error message.
        """
        try:
            project_path = self.base_dir.joinpath(project_name)
            if not project_path.exists():
                return f"Project {project_name} does not exist"
            logger.info(f"Building project {project_name}")
            cmd = ["npm", "run", "build"]
            subprocess.check_call(cmd, cwd=str(project_path))
            return f"Successfully built project {project_name}"
        except Exception as e:
            logger.error(f"Error building project {project_name}: {e}")
            return f"Error building project {project_name}: {e}"

    def stop_project(self) -> str:
        """Stops the running development server."""
        return self.stop_web_server()
