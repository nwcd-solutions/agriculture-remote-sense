# Deployment Guide - Storage and Database Stacks

## Quick Start

### 1. Prerequisites Check

```bash
# Verify Node.js version (18+)
node --version

# Verify AWS CLI is configured
aws sts get-caller-identity

# Verify CDK CLI is installed
cdk --version
```

### 2. Install Dependencies

```bash
cd infrastructure
npm install
```

### 3. Build TypeScript

```bash
npm run build
```

### 4. Verify Stacks

```bash
# Run verification script
./scripts/verify-stacks.sh

# Or manually verify
npm run synth
cdk list
```

Expected output:
```
SatelliteGis-Network-dev
SatelliteGis-Storage-dev
SatelliteGis-Database-dev
```

## Deployment Options

### Option 1: Deploy All Stacks (Recommended)

```bash
# Development environment
npm run deploy:dev

# This will deploy:
# 1. Network Stack (VPC, subnets, security groups)
# 2. Storage Stack (S3 bucket)
# 3. Database Stack (DynamoDB table)
```

### Option 2: Deploy Individual Stacks

```bash
# Deploy only Storage Stack
cdk deploy SatelliteGis-Storage-dev --context environment=dev

# Deploy only Database Stack
cdk deploy SatelliteGis-Database-dev --context environment=dev
```

### Option 3: Deploy with Approval

```bash
# Review changes before deployment
cdk diff --context environment=dev

# Deploy with manual approval for each stack
cdk deploy --all --context environment=dev --require-approval=always
```

## Post-Deployment Verification

### Verify Storage Stack

```bash
# Get bucket name from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Storage-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ResultsBucketName`].OutputValue' \
  --output text

# Verify bucket exists
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Storage-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ResultsBucketName`].OutputValue' \
  --output text)

aws s3 ls s3://$BUCKET_NAME

# Check bucket lifecycle configuration
aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET_NAME

# Check bucket CORS configuration
aws s3api get-bucket-cors --bucket $BUCKET_NAME

# Check bucket encryption
aws s3api get-bucket-encryption --bucket $BUCKET_NAME
```

### Verify Database Stack

```bash
# Get table name from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Database-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`TasksTableName`].OutputValue' \
  --output text

# Verify table exists
TABLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Database-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`TasksTableName`].OutputValue' \
  --output text)

aws dynamodb describe-table --table-name $TABLE_NAME

# Check Global Secondary Indexes
aws dynamodb describe-table --table-name $TABLE_NAME \
  --query 'Table.GlobalSecondaryIndexes[*].IndexName'

# Check TTL configuration
aws dynamodb describe-time-to-live --table-name $TABLE_NAME

# Check DynamoDB Streams
aws dynamodb describe-table --table-name $TABLE_NAME \
  --query 'Table.StreamSpecification'
```

## Testing the Infrastructure

### Test S3 Bucket

```bash
# Create a test file
echo "Test content" > test.txt

# Upload to bucket
aws s3 cp test.txt s3://$BUCKET_NAME/test/test.txt

# Verify upload
aws s3 ls s3://$BUCKET_NAME/test/

# Download file
aws s3 cp s3://$BUCKET_NAME/test/test.txt downloaded.txt

# Verify content
cat downloaded.txt

# Clean up
rm test.txt downloaded.txt
aws s3 rm s3://$BUCKET_NAME/test/test.txt
```

### Test DynamoDB Table

```bash
# Create a test task
aws dynamodb put-item \
  --table-name $TABLE_NAME \
  --item '{
    "task_id": {"S": "test-task-001"},
    "created_at": {"S": "2024-01-28T10:00:00Z"},
    "status": {"S": "queued"},
    "task_type": {"S": "indices"}
  }'

# Query by task_id
aws dynamodb get-item \
  --table-name $TABLE_NAME \
  --key '{
    "task_id": {"S": "test-task-001"},
    "created_at": {"S": "2024-01-28T10:00:00Z"}
  }'

# Query by status using GSI
aws dynamodb query \
  --table-name $TABLE_NAME \
  --index-name StatusIndex \
  --key-condition-expression "status = :status" \
  --expression-attribute-values '{":status":{"S":"queued"}}'

# Clean up
aws dynamodb delete-item \
  --table-name $TABLE_NAME \
  --key '{
    "task_id": {"S": "test-task-001"},
    "created_at": {"S": "2024-01-28T10:00:00Z"}
  }'
```

## Environment-Specific Deployment

### Development Environment

```bash
npm run deploy:dev
```

Configuration:
- S3 lifecycle: 7 days
- DynamoDB: Pay-per-request
- Removal policy: DESTROY
- Point-in-time recovery: Disabled

### Staging Environment

```bash
npm run deploy:staging
```

Configuration:
- S3 lifecycle: 14 days
- DynamoDB: Pay-per-request
- Removal policy: RETAIN
- Point-in-time recovery: Enabled

### Production Environment

```bash
npm run deploy:prod
```

Configuration:
- S3 lifecycle: 30 days
- DynamoDB: Pay-per-request
- Removal policy: RETAIN
- Point-in-time recovery: Enabled

## Troubleshooting

### Issue: CDK Bootstrap Required

**Error:**
```
This stack uses assets, so the toolkit stack must be deployed to the environment
```

**Solution:**
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Issue: Insufficient Permissions

**Error:**
```
User: arn:aws:iam::ACCOUNT:user/USERNAME is not authorized to perform: cloudformation:CreateStack
```

**Solution:**
Ensure your IAM user/role has the following permissions:
- CloudFormation: Full access
- S3: Full access
- DynamoDB: Full access
- IAM: CreateRole, AttachRolePolicy

### Issue: Stack Already Exists

**Error:**
```
Stack [SatelliteGis-Storage-dev] already exists
```

**Solution:**
```bash
# Update existing stack
cdk deploy SatelliteGis-Storage-dev --context environment=dev

# Or destroy and recreate (WARNING: deletes data)
cdk destroy SatelliteGis-Storage-dev --context environment=dev
cdk deploy SatelliteGis-Storage-dev --context environment=dev
```

### Issue: Resource Name Conflict

**Error:**
```
Bucket name already exists
```

**Solution:**
The bucket name includes the account ID to ensure uniqueness. If you still get this error:
1. Check if the bucket exists in your account: `aws s3 ls | grep satellite-gis`
2. Delete the bucket manually: `aws s3 rb s3://BUCKET-NAME --force`
3. Redeploy the stack

## Monitoring Deployment

### View CloudFormation Events

```bash
# Watch stack creation in real-time
aws cloudformation describe-stack-events \
  --stack-name SatelliteGis-Storage-dev \
  --max-items 10

# Check stack status
aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Storage-dev \
  --query 'Stacks[0].StackStatus'
```

### View CDK Deployment Progress

```bash
# Deploy with verbose output
cdk deploy --all --context environment=dev --verbose
```

## Cost Estimation

### Storage Stack
- S3 bucket: $0.023 per GB/month (Standard storage)
- Intelligent Tiering: Automatic cost optimization
- Data transfer: First 100 GB/month free

**Estimated monthly cost (dev):**
- 10 GB storage: ~$0.23/month
- 100 requests: ~$0.01/month
- **Total: ~$0.24/month**

### Database Stack
- DynamoDB: Pay-per-request pricing
- Read: $0.25 per million requests
- Write: $1.25 per million requests
- Storage: $0.25 per GB/month

**Estimated monthly cost (dev):**
- 1,000 reads: ~$0.0003/month
- 1,000 writes: ~$0.0013/month
- 1 GB storage: ~$0.25/month
- **Total: ~$0.25/month**

**Total infrastructure cost (dev): ~$0.50/month**

## Cleanup

### Remove All Stacks

```bash
# Destroy all stacks (WARNING: deletes all data)
cdk destroy --all --context environment=dev

# Or destroy individual stacks
cdk destroy SatelliteGis-Database-dev --context environment=dev
cdk destroy SatelliteGis-Storage-dev --context environment=dev
cdk destroy SatelliteGis-Network-dev --context environment=dev
```

### Manual Cleanup (if CDK destroy fails)

```bash
# Delete S3 bucket (must be empty first)
aws s3 rm s3://$BUCKET_NAME --recursive
aws s3 rb s3://$BUCKET_NAME

# Delete DynamoDB table
aws dynamodb delete-table --table-name $TABLE_NAME

# Delete CloudFormation stacks
aws cloudformation delete-stack --stack-name SatelliteGis-Storage-dev
aws cloudformation delete-stack --stack-name SatelliteGis-Database-dev
```

## Next Steps

After successful deployment:

1. ✅ Verify all resources are created
2. ✅ Test S3 bucket access
3. ✅ Test DynamoDB table operations
4. ⏭️ Deploy Batch Stack (Task 14)
5. ⏭️ Deploy API Stack (Task 14.1)
6. ⏭️ Integrate backend services with infrastructure

## Support

For issues or questions:
1. Check CloudFormation events in AWS Console
2. Review CDK synthesis output: `cdk synth`
3. Check AWS service quotas
4. Review IAM permissions

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
