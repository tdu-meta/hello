# Cloud Deployment Module

## Overview
Deploy Orion as AWS Lambda function with EventBridge scheduling for automated screenings.

## Topics

### 1. Lambda Handler
AWS Lambda entry point for screening execution.

**Lambda Function:**
```python
def handler(event, context) -> dict:
    # Parse event for symbols/strategy
    # Run screening
    # Send notifications for matches
    # Return results
```

**Event Schema:**
```json
{
  "strategy": "ofi",
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "notify": true,
  "dry_run": false
}
```

**Requirements:**
- < 15 minute execution time (Lambda limit)
- Handle 500 symbols within time limit
- Graceful timeout handling
- Structured logging to CloudWatch
- Return success/error response

### 2. Environment Configuration
Lambda environment variables for configuration.

**Required Variables:**
- `ALPHA_VANTAGE_API_KEY` - Data provider key
- `SMTP_HOST`, `SMTP_PORT` - Email server
- `SMTP_USER`, `SMTP_PASSWORD` - Email auth
- `NOTIFICATION_FROM` - From address
- `NOTIFICATION_TO` - Recipients (JSON array)

**Optional Variables:**
- `LOG_LEVEL` - Default INFO
- `CACHE_ENABLED` - Default true
- `MAX_CONCURRENT` - Default 5

### 3. EventBridge Schedule
Automated screening triggers.

**Schedule Options:**
- Every 2 hours during market hours
- Every 4 hours
- Custom cron expression

**Requirements:**
- Enable/disable schedule
- Configure via infrastructure as code
- Pass event to Lambda

### 4. Deployment Infrastructure
Infrastructure as code for deployment.

**AWS Resources:**
- Lambda function with Python 3.12
- Lambda layers for dependencies
- EventBridge rule (schedule)
- CloudWatch Log Group
- IAM role with minimal permissions

**Permissions Needed:**
- CloudWatch Logs (CreateLogStream, PutLogEvents)
- SES (SendEmail) if using AWS SES
- SNS (Publish) if sending SNS notifications

**Requirements:**
- AWS CDK or SAM for infrastructure
- Deployment script
- Environment-specific configs

### 5. Monitoring and Alerting
Operational monitoring for deployed system.

**CloudWatch Metrics:**
- Invocation count
- Error rate
- Duration
- Throttles

**Alarms:**
- Lambda error rate > 5%
- Lambda timeout
- No invocations (schedule stopped)

**Requirements:**
- Dashboard for metrics
- Alarms for failures
- Log aggregation

## Dependencies
- AWS Lambda
- AWS EventBridge
- AWS CloudWatch
- AWS CDK or SAM
- All previous modules

## Files to Create
- `src/orion/lambda_handler.py` - Lambda entry point
- `infrastructure/cdk_app.py` - CDK infrastructure
- `infrastructure/lib/lambda_stack.py` - Lambda stack definition
- `deploy.sh` - Deployment script
- `serverless.yml` or `template.yaml` - SAM template

## Tests Required
- Lambda handler processes events correctly
- Timeout handling
- Error responses
- Local Lambda testing (sam local)
- Integration test with real AWS resources

## Deployment Checklist
- [ ] Lambda function deployed
- [ ] Environment variables configured
- [ ] EventBridge rule active
- [ ] IAM permissions correct
- [ ] CloudWatch logs flowing
- [ ] Test invocation successful
- [ ] Alarms configured

## Rollback Plan
- Keep previous Lambda version
- Can revert with one command
- Database schema migrations backward compatible
