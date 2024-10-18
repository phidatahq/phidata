from typing import List, Dict, Any

from phi.tools.toolkit import Toolkit

try:
    import boto3
except ImportError:
    raise ImportError("boto3 is required for AWSLambdaTool. Please install it using `pip install boto3`.")


class AWSLambdaTool(Toolkit):
    name: str = "AWSLambdaTool"
    description: str = "A tool for interacting with AWS Lambda functions"

    def __init__(self, region_name: str = "us-east-1"):
        super().__init__()
        self.client = boto3.client('lambda', region_name=region_name)

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_functions",
                    "description": "List all Lambda functions in the AWS account",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "invoke_function",
                    "description": "Invoke a Lambda function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "function_name": {"type": "string"},
                            "payload": {"type": "string"}
                        },
                        "required": ["function_name"]
                    }
                }
            }
        ]

    def list_functions(self) -> Dict[str, Any]:
        try:
            response = self.client.list_functions()
            return {"functions": [func['FunctionName'] for func in response['Functions']]}
        except Exception as e:
            return {"error": str(e)}

    def invoke_function(self, function_name: str, payload: str = "{}") -> Dict[str, Any]:
        try:
            response = self.client.invoke(
                FunctionName=function_name,
                Payload=payload
            )
            return {
                "status_code": response['StatusCode'],
                "payload": response['Payload'].read().decode('utf-8')
            }
        except Exception as e:
            return {"error": str(e)}
