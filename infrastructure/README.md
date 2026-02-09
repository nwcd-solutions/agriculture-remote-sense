# Satellite GIS Platform - AWS CDK Infrastructure

This directory contains the AWS CDK infrastructure code for the Satellite GIS Platform.

## Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed globally: `npm install -g aws-cdk`

## Project Structure

```
infrastructure/
├── bin/
│   └── satellite-gis.ts          # CDK app entry point
├── lib/
│   ├── stacks/
│   │   └── network-stack.ts      # VPC, subnets, security groups
│   ├── constructs/               # Reusable CDK constructs
│   └── config/
│       ├── types.ts              # Configuration type definitions
│       ├── dev.ts                # Development environment config
│       ├── staging.ts            # Staging environment config
│       ├── prod.ts               # Production environment config
│       └── index.ts              # Config loader
├── cdk.json                      # CDK configuration
├── tsconfig.json                 # TypeScript configuration
└── package.json                  # Node.js dependencies
```

## Installation

Install dependencies:

```bash
cd infrastructure
npm install
```

## Configuration

Environment-specific configurations are located in `lib/config/`:

- `dev.ts` - Development environment (minimal resources)
- `staging.ts` - Staging environment (moderate resources)
- `prod.ts` - Production environment (full resources)

### Environment Variables

Set the following environment variables before deployment:

```bash
export CDK_DEFAULT_ACCOUNT=<your-aws-account-id>
export CDK_DEFAULT_REGION=<your-aws-region>
export ALARM_EMAIL=<your-email-for-alarms>
```

**Note**: Frontend Stack deployment via CDK requires GitHub token. For simpler deployment, you can:
1. Skip the Frontend Stack and manually set up Amplify via AWS Console (OAuth connection)
2. Or deploy frontend to S3 + CloudFront manually
3. Or set `GITHUB_TOKEN` environment variable if you prefer automated deployment

## Usage

### Build TypeScript

```bash
npm run build
```

### Watch for changes

```bash
npm run watch
```

### Synthesize CloudFormation templates

```bash
npm run synth
```

### Deploy to specific environment

```bash
# Deploy to dev (default)
npm run deploy:dev

# Deploy to staging
npm run deploy:staging

# Deploy to production
npm run deploy:prod
```

### View differences before deployment

```bash
npm run diff
```

### Bootstrap CDK (first time only)

Before deploying for the first time, bootstrap your AWS environment:

```bash
cdk bootstrap aws://<account-id>/<region>
```

## Stacks

### Network Stack

Creates the foundational network infrastructure:

- **VPC** with public and private subnets across multiple AZs
- **NAT Gateways** for private subnet internet access
- **Security Groups** for Batch, API, and Database
- **VPC Endpoints** for S3, DynamoDB, ECR, and CloudWatch Logs (cost optimization)

**Outputs:**
- VPC ID
- Security Group IDs
- Subnet IDs

### Storage Stack

Creates S3 storage infrastructure for processing results:

- **S3 Bucket** with encryption and lifecycle rules
- **Lifecycle Rules**:
  - Task results: Expires after 30 days (7 days in dev)
  - Temporary files: Expires after 1 day
  - Logs: Expires after 7 days
  - Intelligent tiering after 7 days for cost optimization
- **CORS Configuration** for frontend access
- **Event notifications** enabled for future Lambda triggers

**Outputs:**
- Bucket name
- Bucket ARN
- Bucket domain name

### Database Stack

Creates DynamoDB tables for task management:

- **ProcessingTasks Table**:
  - Partition key: `task_id` (String)
  - Sort key: `created_at` (String)
  - Pay-per-request billing mode
- **Global Secondary Indexes**:
  - StatusIndex: Query tasks by status
  - BatchJobIndex: Query tasks by Batch job ID
  - UserIndex: Query tasks by user (for future authentication)
- **TTL Configuration**: Automatic cleanup of expired tasks
- **Point-in-time Recovery**: Enabled for production environment
- **DynamoDB Streams**: Enabled for event processing

**Outputs:**
- Table name
- Table ARN
- Stream ARN

## Cost Optimization

The infrastructure is designed with cost optimization in mind:

1. **VPC Endpoints**: Gateway endpoints for S3 and DynamoDB (free) reduce NAT Gateway data transfer costs
2. **NAT Gateways**: Number varies by environment (1 for dev, 2 for staging, 3 for prod)
3. **Spot Instances**: AWS Batch configured to use Spot instances (70-80% discount)
4. **Auto-scaling**: Resources scale down to zero when not in use

## Security

- All resources deployed in private subnets where possible
- Security groups follow principle of least privilege
- VPC endpoints reduce exposure to public internet
- All traffic encrypted in transit

## Monitoring

CloudWatch Logs and metrics are automatically configured for all resources.

## Cleanup

To destroy all resources:

```bash
cdk destroy --all
```

**Warning**: This will delete all resources including data in S3 and DynamoDB.

## Troubleshooting

### CDK Bootstrap Error

If you see "CDK bootstrap required" error:

```bash
cdk bootstrap aws://<account-id>/<region>
```

### TypeScript Compilation Errors

Ensure you have the correct Node.js version:

```bash
node --version  # Should be 18+
```

Rebuild:

```bash
npm run build
```

### Deployment Failures

Check CloudFormation events in AWS Console for detailed error messages.

## Next Steps

After deploying the Network Stack, you can proceed to deploy:

1. Storage Stack (S3 buckets)
2. Database Stack (DynamoDB tables)
3. Batch Stack (AWS Batch compute environment)
4. API Stack (ECS/Fargate service)
5. Frontend Stack (S3 + CloudFront)
6. Monitoring Stack (CloudWatch dashboards and alarms)
