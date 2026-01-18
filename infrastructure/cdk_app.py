"""AWS CDK application for Orion stock screening Lambda deployment.

This module defines the CDK app that deploys the Orion screening Lambda function
with EventBridge scheduling, CloudWatch monitoring, and IAM permissions.
"""

import os
from pathlib import Path

from aws_cdk import App, CfnOutput, Duration

from infrastructure.lib.orion_stack import OrionStack

# Configuration from environment
STACK_NAME = os.environ.get("CDK_STACK_NAME", "OrionStack")
REGION = os.environ.get("CDK_DEPLOY_REGION", "us-east-1")
ACCOUNT_ID = os.environ.get("CDK_DEPLOY_ACCOUNT", "123456789012")


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_strategy_file_path() -> str:
    """Get the path to the OFI strategy file for Lambda layer."""
    project_root = get_project_root()
    strategy_path = project_root / "strategies" / "ofi.yaml"
    return str(strategy_path.absolute())


def get_lambda_code_path() -> str:
    """Get the path to the Lambda handler code."""
    project_root = get_project_root()
    # Lambda code will be packaged separately
    return str((project_root / "src" / "orion").absolute())


def get_requirements_path() -> str:
    """Get the path to requirements.txt for Lambda layer."""
    project_root = get_project_root()
    return str((project_root / "requirements.txt").absolute())


app = App()

# Environment-specific configuration
env = {
    "account": ACCOUNT_ID,
    "region": REGION,
}

# Create the Orion stack
orion_stack = OrionStack(
    app,
    STACK_NAME,
    description="Orion stock screening Lambda function with EventBridge scheduling",
    env=env,
    # Lambda configuration
    lambda_code_path=get_lambda_code_path(),
    strategy_file_path=get_strategy_file_path(),
    requirements_path=get_requirements_path(),
    # Runtime configuration
    lambda_timeout=Duration.minutes(15),
    lambda_memory_size=1024,
    # Scheduling configuration
    schedule_expression=os.environ.get("SCHEDULE_EXPRESSION", "rate(2 hours)"),
    # Default symbols for scheduled runs
    default_symbols=os.environ.get(
        "DEFAULT_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,JNJ,V"
    ),
)

# CloudFormation outputs for reference
CfnOutput(
    app,
    "LambdaFunctionName",
    value=orion_stack.lambda_function.function_name,
    description="Name of the Orion Lambda function",
)

CfnOutput(
    app,
    "LambdaFunctionArn",
    value=orion_stack.lambda_function.function_arn,
    description="ARN of the Orion Lambda function",
)

CfnOutput(
    app,
    "EventBridgeRuleName",
    value=orion_stack.schedule_rule.rule_name if orion_stack.schedule_rule else "Disabled",
    description="Name of the EventBridge schedule rule",
)

CfnOutput(
    app,
    "LogGroupName",
    value=orion_stack.log_group.log_group_name,
    description="Name of the CloudWatch Log Group",
)

app.synth()
