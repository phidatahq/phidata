import requests
from os import getenv
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

    # issue related methods

    def get_user_details(self):
        """Fetch authenticated user details"""

        query = """
        query Me {
          viewer {
            id
            name
            email
          }
        }
        """

        try:
            user = self._execute_query(query)["user"]
            logger.info("Retrieved authenticated user details")
            return user

        except Exception as e:
            logger.error(f"Error fetching authenticated user details: {e}")
            raise

    def get_issue_details(self, issue_id):
      """Retrieve details of a specific issue by issue ID."""

      query = """
      query IssueDetails($issueId: ID!) {
        issue(id: $issueId) {
          id
          title
          description
        }
      }
      """
      variables = {"issueId": issue_id}
      try:
          response = self._execute_query(query, variables)

          if response.get("issue"):
              issue = response["issue"]
              logger.info(f"Issue '{issue['title']}' retrieved successfully with ID {issue['id']}.")
              return issue
          else:
              logger.error(f"Failed to retrieve issue with ID {issue_id}.")
              return None

      except Exception as e:
          logger.error(f"Error retrieving issue with ID {issue_id}: {e}")
          raise


    def create_issue(self, title, description, team_id):
        """Create a new issue within a specific project and team."""

        query = """
        mutation IssueCreate{
          issueCreate(
            input: { title: $title, description: $description, teamId: $teamId }
          ) {
            success
            issue {
              id
              title
            }
          }
        }
        """
        variables = {"title": title, "description": description, "teamId": team_id}
        try:
            response = self._execute_query(query, variables)

            if response["issueCreate"]["success"]:
                issue = response["issueCreate"]["issue"]
                logger.info(f"Issue '{issue['title']}' created successfully with ID {issue['id']}")
                return issue
            else:
                logger.error("Issue creation failed.")
                return None

        except Exception as e:
            logger.error(f"Error creating issue '{title}' for team ID {team_id}: {e}")
            raise

    def update_issue(self, issue_id, title=None, state_id=None):
        """Update details of an existing issue, such as title and state_id."""

        query = """
        mutation IssueUpdate {
          issueUpdate(
            id: $issueId,
            input: { title: $title, stateId: $stateId }
          ) {
            success
            issue {
              id
              title
              state {
                id
                name
              }
            }
          }
        }
        """
        variables = {"issueId": issue_id, "title": title, "stateId": state_id}

        try:
            response = self._execute_query(query, variables)

            if response["issueUpdate"]["success"]:
                issue = response["issueUpdate"]["issue"]
                logger.info(f"Issue ID {issue_id} updated successfully.")
                return issue
            else:
                logger.error(f"Failed to update issue ID {issue_id}. Success flag was false.")
                return None

        except Exception as e:
            logger.error(f"Error updating issue ID {issue_id}: {e}")
            raise

    def get_user_assigned_issues(self, user_id):
        """Retrieve issues assigned to a specific user by user ID."""

        query = """
      query UserAssignedIssues($userId: ID!) {
        user(id: $userId) {
          id
          name
          assignedIssues {
            nodes {
              id
              title
            }
          }
        }
      }
      """
        variables = {"userId": user_id}

        try:
            response = self._execute_query(query, variables)

            if response.get("user"):
                user = response["user"]
                issues = user["assignedIssues"]["nodes"]
                logger.info(f"Retrieved {len(issues)} issues assigned to user '{user['name']}' (ID: {user['id']}).")
                return issues
            else:
                logger.error("Failed to retrieve user or issues.")
                return None

        except Exception as e:
            logger.error(f"Error retrieving issues for user ID {user_id}: {e}")
            raise

    def get_workflow_issues(self, workflow_id):
        """Retrieve issues within a specific workflow state by workflow ID."""

        query = """
      query WorkflowStateIssues($workflowId: ID!) {
        workflowState(id: $workflowId) {
          issues {
            nodes {
              title
            }
          }
        }
      }
      """
        variables = {"workflowId": workflow_id}
        try:
            response = self._execute_query(query, variables)

            if response.get("workflowState"):
                issues = response["workflowState"]["issues"]["nodes"]
                logger.info(f"Retrieved {len(issues)} issues in workflow state ID {workflow_id}.")
                return issues
            else:
                logger.error("Failed to retrieve issues for the specified workflow state.")
                return None

        except Exception as e:
            logger.error(f"Error retrieving issues for workflow state ID {workflow_id}: {e}")
            raise

    def get_high_priority_issues(self):
        """Retrieve issues with a high priority (priority <= 2)."""

        query = """
      query HighPriorityIssues {
        issues(filter: { 
          priority: { lte: 2 }
        }) {
          nodes {
            id
            title
            priority
          }
        }
      }
      """
        try:
            response = self._execute_query(query)

            if response.get("issues"):
                high_priority_issues = response["issues"]["nodes"]
                logger.info(f"Retrieved {len(high_priority_issues)} high-priority issues.")
                return high_priority_issues
            else:
                logger.error("Failed to retrieve high-priority issues.")
                return None

        except Exception as e:
            logger.error(f"Error retrieving high-priority issues: {e}")
            raise
