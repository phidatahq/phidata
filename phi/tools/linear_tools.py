from os import getenv
import requests
from phi.tools import Toolkit
from phi.utils.log import logger


class LinearTool(Toolkit):
    def __init__(self):
        super().__init__(name="linear tools")
        self.api_token = getenv("LINEAR_API_KEY")
        self.endpoint = "https://api.linear.app/graphql"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    def _execute_query(self, query, variables=None):
        """Helper method to execute GraphQL queries with optional variables."""

        try:
            response = requests.post(self.endpoint, json={"query": query, "variables": variables}, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            if "errors" in data:
                logger.error(f"GraphQL Error: {data['errors']}")
                raise Exception(f"GraphQL Error: {data['errors']}")

            logger.info("GraphQL query executed successfully.")
            return data.get("data")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    # Issue-related methods
    def get_issues_by_project(self, project_id):
        """Fetch all issues associated with a specific project."""

        logger.info(f"Fetching issues for project ID: {project_id}")
        query = """
        query GetIssuesByProject($projectId: String!) {
          issues(filter: { projectId: $projectId }) {
            nodes {
              id
              title
              description
            }
          }
        }
        """
        variables = {"projectId": project_id}
        try:
            issues = self._execute_query(query, variables)["issues"]["nodes"]
            logger.info(f"Retrieved {len(issues)} issues for project ID {project_id}")
            return issues

        except Exception as e:
            logger.error(f"Error fetching issues for project ID {project_id}: {e}")
            raise

    def get_issue_details(self, issue_id):
        """Fetch detailed information about a specific issue by its ID."""

        query = """
        query GetIssueDetails($issueId: String!) {
          issue(id: $issueId) {
            id
            title
            description
            status {
              name
            }
            assignee {
              name
            }
            comments {
              nodes {
                body
              }
            }
          }
        }
        """
        variables = {"issueId": issue_id}
        try:
            issue = self._execute_query(query, variables)["issue"]
            logger.info(f"Retrieved details for issue ID {issue_id}")
            return issue

        except Exception as e:
            logger.error(f"Error fetching details for issue ID {issue_id}: {e}")
            raise

    def create_issue(self, title, description, project_id, team_id):
        """Create a new issue within a specific project and team."""

        query = """
        mutation CreateIssue($title: String!, $description: String, $projectId: String, $teamId: String!) {
          issueCreate(
            input: { title: $title, description: $description, projectId: $projectId, teamId: $teamId }
          ) {
            issue {
              id
              title
            }
          }
        }
        """
        variables = {"title": title, "description": description, "projectId": project_id, "teamId": team_id}
        try:
            issue = self._execute_query(query, variables)["issueCreate"]["issue"]
            logger.info(f"Issue '{title}' created successfully with ID {issue['id']}")
            return issue

        except Exception as e:
            logger.error(f"Error creating issue '{title}' for project ID {project_id}: {e}")
            raise

    def update_issue(self, issue_id, title=None, description=None, status_id=None):
        """Update details of an existing issue, such as title, description, or status."""

        query = """
        mutation UpdateIssue($issueId: String!, $title: String, $description: String, $statusId: String) {
          issueUpdate(
            id: $issueId,
            input: { title: $title, description: $description, statusId: $statusId }
          ) {
            issue {
              id
              title
              description
              status {
                name
              }
            }
          }
        }
        """
        variables = {"issueId": issue_id, "title": title, "description": description, "statusId": status_id}
        try:
            issue = self._execute_query(query, variables)["issueUpdate"]["issue"]
            logger.info(f"Issue ID {issue_id} updated successfully.")
            return issue

        except Exception as e:
            logger.error(f"Error updating issue ID {issue_id}: {e}")
            raise

    def delete_issue(self, issue_id):
        """Delete an issue by its ID."""

        query = """
        mutation DeleteIssue($issueId: String!) {
          issueDelete(id: $issueId) {
            success
          }
        }
        """
        variables = {"issueId": issue_id}
        try:
            issue = self._execute_query(query, variables)["issueDelete"]["success"]
            logger.info(f"Issue ID {issue_id} deleted successfully.")
            return issue

        except Exception as e:
            logger.error(f"Error deleting issue ID {issue_id}: {e}")
            raise

    # Project-related methods
    def get_projects(self):
        """Fetch all projects in the workspace."""

        logger.info("Fetching all projects in the workspace")
        query = """
        query GetProjects {
          projects {
            nodes {
              id
              name
              description
            }
          }
        }
        """
        try:
            projects = self._execute_query(query)["projects"]["nodes"]
            logger.info(f"Retrieved {len(projects)} projects")
            return projects

        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            raise

    def get_project_details(self, project_id):
        """Retrieve details of a specific project."""

        logger.info(f"Fetching details for project ID: {project_id}")
        query = """
        query GetProjectDetails($projectId: String!) {
          project(id: $projectId) {
            id
            name
            description
            issues {
              nodes {
                id
                title
              }
            }
          }
        }
        """
        variables = {"projectId": project_id}
        try:
            project = self._execute_query(query, variables)["project"]
            logger.info(f"Retrieved details for project ID {project_id}")
            return project
        except Exception as e:
            logger.error(f"Error fetching details for project ID {project_id}: {e}")
            raise

    def create_project(self, name, description, team_id):
        """Create a new project within a specific team."""

        logger.info(f"Creating project '{name}' for team ID: {team_id}")
        query = """
        mutation CreateProject($name: String!, $description: String, $teamId: String!) {
          projectCreate(
            input: { name: $name, description: $description, teamId: $teamId }
          ) {
            project {
              id
              name
            }
          }
        }
        """
        variables = {"name": name, "description": description, "teamId": team_id}
        try:
            project = self._execute_query(query, variables)["projectCreate"]["project"]
            logger.info(f"Project '{name}' created successfully with ID {project['id']}")
            return project
        except Exception as e:
            logger.error(f"Error creating project '{name}': {e}")
            raise

    def delete_project(self, project_id):
        """Delete a project by its ID."""

        logger.info(f"Deleting project ID: {project_id}")
        query = """
        mutation DeleteProject($projectId: String!) {
          projectDelete(id: $projectId) {
            success
          }
        }
        """
        variables = {"projectId": project_id}
        try:
            success = self._execute_query(query, variables)["projectDelete"]["success"]
            if success:
                logger.info(f"Project ID {project_id} deleted successfully.")
            else:
                logger.warning(f"Project ID {project_id} could not be deleted.")
            return success
        except Exception as e:
            logger.error(f"Error deleting project ID {project_id}: {e}")
            raise

    # Team-related methods
    def get_teams(self):
        """Fetch all teams in the workspace."""

        logger.info("Fetching all teams in the workspace")
        query = """
        query GetTeams {
          teams {
            nodes {
              id
              name
              key
            }
          }
        }
        """
        try:
            teams = self._execute_query(query)["teams"]["nodes"]
            logger.info(f"Retrieved {len(teams)} teams")
            return teams
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            raise

    # Comment-related methods
    def add_comment_to_issue(self, issue_id, body):
        """Add a comment to a specific issue."""

        logger.info(f"Adding comment to issue ID: {issue_id}")
        query = """
        mutation AddCommentToIssue($issueId: String!, $body: String!) {
          commentCreate(
            input: { issueId: $issueId, body: $body }
          ) {
            comment {
              id
              body
            }
          }
        }
        """
        variables = {"issueId": issue_id, "body": body}
        try:
            comment = self._execute_query(query, variables)["commentCreate"]["comment"]
            logger.info(f"Comment added to issue ID {issue_id} with comment ID {comment['id']}")
            return comment

        except Exception as e:
            logger.error(f"Error adding comment to issue ID {issue_id}: {e}")
            raise

    def get_comments_by_issue(self, issue_id):
        """Retrieve all comments for a specific issue."""

        logger.info(f"Fetching comments for issue ID: {issue_id}")
        query = """
        query GetCommentsByIssue($issueId: String!) {
          issue(id: $issueId) {
            comments {
              nodes {
                id
                body
                createdAt
              }
            }
          }
        }
        """
        variables = {"issueId": issue_id}
        try:
            comments = self._execute_query(query, variables)["issue"]["comments"]["nodes"]
            logger.info(f"Retrieved {len(comments)} comments for issue ID {issue_id}")
            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for issue ID {issue_id}: {e}")
            raise
