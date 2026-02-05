# Infrastructure Stacks

This directory contains AWS CDK stack definitions for the Satellite GIS Platform.

## Stacks Overview

### 1. Network Stack (`network-stack.ts`)
Creates the VPC and networking infrastructure:
- VPC with public and private subnets across multiple availability zones
- NAT Gateway for private subnet internet access
- Security groups for Batch compute and API services
- VPC endpoints for AWS services (optional)

**Outputs:**
- VPC ID
- Subnet IDs
- Security Group IDs

### 2. Storage Stack (`storage-stack.ts`)
Creates S3 storage infrastructure:
- S3 bucket for processing results with encryption
- Lifecycle rules for automatic cleanup:
  - Task results: 30 days (configurable per environment)
  - Temporary files: 1 day
  - Logs: 7 days (configurable)
- CORS configuration for frontend access
- Intelligent tiering for cost optimization

**Outputs:**
- Bucket name
- Bucket ARN
- Bucket domain name

### 3. Database Stack (`database-stack.ts`)
Creates DynamoDB tables for task management:
- ProcessingTasks table with partition key (task_id) and sort key (created_at)
- Global Secondary Indexes:
  - StatusIndex: Query tasks by status
  - BatchJobIndex: Query tasks by Batch job ID
  - UserIndex: Query tasks by user (for future authentication)
- TTL enabled for automatic cleanup of expired tasks
- Point-in-time recovery enabled for production
- DynamoDB Streams enabled for event processing

**Outputs:**
- Table name
- Table ARN
- Stream ARN

## Configuration

Each stack uses environment-specific configuration from `lib/config/`:
- `dev.ts`: Development environment (7-day retention, minimal resources)
- `staging.ts`: Staging environment (14-day retention, moderate resources)
- `prod.ts`: Production environment (30-day retention, high availability)

## Deployment

### Prerequisites
```bash
# Install dependencies
npm install

# Configure AWS credentials
aws configure

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Deploy All Stacks
```bash
# Development environment
npm run deploy:dev

# Staging environment
npm run deploy:staging

# Production environment
npm run deploy:prod
```

### Deploy Individual Stacks
```bash
# Deploy only storage stack
cdk deploy SatelliteGis-Storage-dev --context environment=dev

# Deploy only database stack
cdk deploy SatelliteGis-Database-dev --context environment=dev
```

### View Changes Before Deployment
```bash
cdk diff --context environment=dev
```

### Destroy Stacks
```bash
# Destroy all stacks (be careful!)
cdk destroy --all --context environment=dev
```

## Stack Dependencies

```
NetworkStack (no dependencies)
    ↓
StorageStack (no dependencies)
    ↓
DatabaseStack (no dependencies)
    ↓
BatchStack (depends on: Network, Storage, Database)
    ↓
ApiStack (depends on: Network, Storage, Database, Batch)
    ↓
FrontendStack (depends on: Api)
    ↓
MonitoringStack (depends on: Api, Batch, Database)
```

## Resource Naming Convention

All resources follow the naming pattern:
```
{ResourceType}-{Environment}-{OptionalSuffix}
```

Examples:
- `ProcessingTasks-dev`
- `satellite-gis-results-dev-123456789012`
- `SatelliteGis-Network-prod`

## Cost Optimization

### Storage Stack
- Lifecycle rules automatically delete old files
- Intelligent tiering moves infrequently accessed data to cheaper storage
- Abort incomplete multipart uploads after 1 day

### Database Stack
- Pay-per-request billing mode (no idle costs)
- TTL automatically deletes expired records
- GSI projections optimized for query patterns

### Network Stack
- Single NAT Gateway in dev (multiple in prod for HA)
- VPC endpoints reduce data transfer costs (optional)

## Security Features

### Storage Stack
- S3 bucket encryption enabled (S3-managed keys)
- Block all public access
- CORS restricted to specific origins (TODO: configure in production)
- Versioning disabled to reduce costs

### Database Stack
- Encryption at rest enabled by default
- Point-in-time recovery for production
- IAM-based access control
- DynamoDB Streams for audit logging

### Network Stack
- Private subnets for compute resources
- Security groups with least privilege access
- VPC flow logs enabled (optional)

## Monitoring and Logging

All stacks include:
- CloudWatch metrics for resource utilization
- CloudFormation stack outputs for easy reference
- Resource tagging for cost allocation
- EventBridge integration for event-driven workflows

## Troubleshooting

### Stack Deployment Fails
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify CDK bootstrap: `cdk bootstrap --show-template`
3. Check CloudFormation console for detailed error messages

### Resource Already Exists
If a resource name conflicts:
1. Update the resource name in the stack
2. Or delete the existing resource manually
3. Redeploy the stack

### Permission Denied
Ensure your IAM user/role has permissions:
- CloudFormation full access
- S3 full access
- DynamoDB full access
- EC2 full access (for VPC)
- IAM role creation

## Next Steps

After deploying these stacks:
1. Deploy Batch Stack for compute resources
2. Deploy API Stack for backend services
3. Deploy Frontend Stack for web interface
4. Deploy Monitoring Stack for observability

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html)
