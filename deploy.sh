#!/bin/bash
# Deployment script for Orion AWS Lambda function
#
# This script deploys the Orion screening Lambda function using AWS CDK.
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - Node.js 18+ and Python 3.12 installed
# - CDK CLI installed: npm install -g aws-cdk
# - Docker running (for bundling Lambda layers)
#
# Usage:
#   ./deploy.sh                    # Deploy to default account/region
#   ./deploy.sh --profile prod     # Deploy with specific AWS profile
#   ./deploy.sh --no-schedule      # Deploy without EventBridge scheduling

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default configuration
STACK_NAME="OrionStack"
SCHEDULE_ENABLED="true"
SCHEDULE_EXPRESSION="rate(2 hours)"
DEFAULT_SYMBOLS="AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,JNJ,V"
AWS_PROFILE=""
AWS_REGION="us-east-1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --no-schedule)
            SCHEDULE_ENABLED="false"
            shift
            ;;
        --schedule)
            SCHEDULE_EXPRESSION="$2"
            shift 2
            ;;
        --symbols)
            DEFAULT_SYMBOLS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE      AWS CLI profile to use"
            echo "  --region REGION        AWS region to deploy to (default: us-east-1)"
            echo "  --no-schedule          Deploy without EventBridge scheduling"
            echo "  --schedule EXPR        Cron expression for schedule (default: 'rate(2 hours)')"
            echo "  --symbols SYMBOLS      Comma-separated default symbols"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build AWS CLI command
AWS_CMD="aws"
if [ -n "$AWS_PROFILE" ]; then
    AWS_CMD="$AWS_CMD --profile $AWS_PROFILE"
fi

echo -e "${GREEN}=== Orion Lambda Deployment Script ===${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "${YELLOW}>>> $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify prerequisites
print_section "Verifying Prerequisites"

# Check Python
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "Node.js version: $NODE_VERSION"

# Check AWS CDK
if ! command_exists cdk; then
    echo "CDK CLI not found. Installing globally..."
    npm install -g aws-cdk
fi

CDK_VERSION=$(cdk --version)
echo "CDK version: $CDK_VERSION"

# Check Docker (for bundling layers)
if ! command_exists docker; then
    echo -e "${YELLOW}Warning: Docker is not running. Lambda layers may not build correctly.${NC}"
else
    DOKCER_VERSION=$(docker --version)
    echo "Docker: $DOKCER_VERSION"
fi

# Check Poetry
if ! command_exists poetry; then
    echo -e "${YELLOW}Warning: Poetry not found. Attempting to use pip...${NC}"
    PIP_CMD="python3 -m pip"
else
    PIP_CMD="poetry run pip"
fi

# Check AWS credentials
print_section "Checking AWS Credentials"

if [ -n "$AWS_PROFILE" ]; then
    echo "Using AWS profile: $AWS_PROFILE"
fi

# Get account ID
ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Could not retrieve AWS account ID. Check AWS credentials.${NC}"
    exit 1
fi

echo "AWS Account: $ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Install dependencies
print_section "Installing Dependencies"

# Install Python dependencies
if command_exists poetry; then
    echo "Installing Python dependencies with Poetry..."
    poetry install --no-root
else
    echo "Installing Python dependencies with pip..."
    python3 -m pip install --upgrade pip
    python3 -m pip install aws-cdk-lib constructs
fi

# Install CDK dependencies in infrastructure directory
cd infrastructure
if [ ! -d "node_modules" ]; then
    echo "Installing CDK node modules..."
    npm install
fi
cd ..

# Bootstrap CDK if needed
print_section "Checking CDK Bootstrap"

BOOTSTRAPPED=$($AWS_CMD cloudformation describe-stacks \
    --stack-name "cdk-${ACCOUNT_ID}-${AWS_REGION}" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackName' \
    --output text 2>/dev/null || echo "")

if [ "$BOOTSTRAPPED" != "cdk-${ACCOUNT_ID}-${AWS_REGION}" ]; then
    echo "CDK not bootstrapped. Bootstrapping..."
    cdk bootstrap \
        --profile "$AWS_PROFILE" \
        "aws://${ACCOUNT_ID}/${AWS_REGION}"
else
    echo "CDK already bootstrapped in region $AWS_REGION"
fi

# Set environment variables for CDK deployment
export CDK_DEPLOY_ACCOUNT=$ACCOUNT_ID
export CDK_DEPLOY_REGION=$AWS_REGION
export CDK_STACK_NAME=$STACK_NAME
export SCHEDULE_ENABLED=$SCHEDULE_ENABLED
export SCHEDULE_EXPRESSION=$SCHEDULE_EXPRESSION
export DEFAULT_SYMBOLS=$DEFAULT_SYMBOLS

# Pass through sensitive environment variables if they exist
if [ -n "$ALPHA_VANTAGE_API_KEY" ]; then
    export ALPHA_VANTAGE_API_KEY
fi
if [ -n "$SMTP_HOST" ]; then
    export SMTP_HOST
fi
if [ -n "$SMTP_PORT" ]; then
    export SMTP_PORT
fi
if [ -n "$SMTP_USER" ]; then
    export SMTP_USER
fi
if [ -n "$SMTP_PASSWORD" ]; then
    export SMTP_PASSWORD
fi
if [ -n "$NOTIFICATION_FROM" ]; then
    export NOTIFICATION_FROM
fi
if [ -n "$NOTIFICATION_TO" ]; then
    export NOTIFICATION_TO
fi

# Deploy
print_section "Deploying Stack"

cd infrastructure

# Synthesize CloudFormation template
echo "Synthesizing CloudFormation template..."
cdk synth

# Deploy stack
echo "Deploying stack: $STACK_NAME"
cdk deploy \
    --profile "$AWS_PROFILE" \
    --require-approval never \
    --progress events \
    "$STACK_NAME"

cd ..

# Output deployment info
print_section "Deployment Complete"

echo "Stack: $STACK_NAME"
echo "Region: $AWS_REGION"
echo "Account: $ACCOUNT_ID"
echo ""
echo "To invoke the Lambda function manually:"
echo "  $AWS_CMD lambda invoke \\"
echo "    --function-name orion-screening \\"
echo "    --region $AWS_REGION \\"
echo "    --payload '{\"strategy\":\"ofi\",\"symbols\":[\"AAPL\"],\"notify\":false}' \\"
echo "    response.json"
echo ""
echo "To view CloudWatch logs:"
echo "  $AWS_CMD logs tail /aws/lambda/orion-screening --region $AWS_REGION --follow"
