# Frontend Stack

## Overview

The Frontend Stack provides static website hosting infrastructure for the Satellite GIS Platform frontend application using Amazon S3 and CloudFront CDN.

## Architecture

```
User Browser
    ↓
CloudFront Distribution (CDN)
    ↓
S3 Bucket (Static Website)
    ├── index.html
    ├── static/
    │   ├── js/
    │   ├── css/
    │   └── media/
    └── config.json (API URL)
```

## Components

### 1. S3 Bucket for Static Website Hosting

- **Purpose**: Hosts the React frontend build files
- **Configuration**:
  - Website hosting enabled with `index.html` as default document
  - Error document set to `index.html` for SPA routing
  - Private access (accessed via CloudFront OAI)
  - Versioning enabled in production
  - CORS configured for API calls

### 2. CloudFront Distribution

- **Purpose**: Global CDN for fast content delivery
- **Features**:
  - HTTPS redirect enforced
  - Compression enabled
  - Custom error responses for SPA routing (403/404 → index.html)
  - IPv6 enabled
  - Configurable price class per environment
  - Optional custom domain support
  - Access logging (optional)

### 3. Origin Access Identity (OAI)

- **Purpose**: Secure access from CloudFront to S3
- **Benefit**: S3 bucket remains private, only accessible via CloudFront

## Configuration

### Environment-Specific Settings

**Development:**
- Price Class: 100 (US, Canada, Europe)
- No custom domain
- Bucket auto-delete on stack deletion

**Staging:**
- Price Class: 200 (US, Canada, Europe, Asia, Middle East, Africa)
- Optional custom domain
- Bucket auto-delete on stack deletion

**Production:**
- Price Class: All (All edge locations)
- Custom domain support
- Bucket retained on stack deletion
- Versioning enabled

### Custom Domain Setup

To use a custom domain:

1. Create an ACM certificate in `us-east-1` region (required for CloudFront)
2. Set the certificate ARN in environment config:
   ```typescript
   frontend: {
     domainName: 'app.example.com',
     certificateArn: 'arn:aws:acm:us-east-1:...',
     enableCloudFront: true,
     cloudFrontPriceClass: 'PriceClass_All',
   }
   ```
3. After deployment, create a CNAME record pointing to the CloudFront distribution domain

## Outputs

The stack exports the following values:

- **WebsiteBucketName**: S3 bucket name for deployment
- **WebsiteUrl**: Frontend URL (CloudFront or S3 website endpoint)
- **DistributionId**: CloudFront distribution ID (for cache invalidation)
- **DistributionDomainName**: CloudFront domain name
- **CustomDomain**: Custom domain (if configured)
- **FrontendConfig**: JSON configuration with API URL

## Deployment

### 1. Deploy Infrastructure

```bash
cd infrastructure
npm run build
cdk deploy SatelliteGis-Frontend-dev
```

### 2. Build Frontend

```bash
cd frontend
npm run build
```

### 3. Deploy Frontend Files

```bash
# Get bucket name from stack outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Frontend-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
  --output text)

# Sync build files to S3
aws s3 sync build/ s3://$BUCKET_NAME/ --delete

# Invalidate CloudFront cache (if using CloudFront)
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name SatelliteGis-Frontend-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

## Frontend Configuration

The frontend needs to know the API URL. This can be configured in two ways:

### Option 1: Environment Variable at Build Time

```bash
# In frontend/.env
REACT_APP_API_URL=https://api.example.com
```

### Option 2: Runtime Configuration

Create a `config.json` file in the S3 bucket:

```json
{
  "apiUrl": "https://api.example.com",
  "environment": "dev"
}
```

The frontend can fetch this at runtime:

```javascript
fetch('/config.json')
  .then(res => res.json())
  .then(config => {
    // Use config.apiUrl
  });
```

## SPA Routing

The stack is configured to support Single Page Application (SPA) routing:

- CloudFront error responses redirect 403/404 to `index.html`
- This allows client-side routing (React Router) to work correctly
- Users can bookmark and refresh any route

## Security

- S3 bucket is private (no public access)
- CloudFront uses Origin Access Identity (OAI) to access S3
- HTTPS enforced via CloudFront
- CORS configured for API calls
- Optional custom domain with ACM certificate

## Cost Optimization

- **Development**: Price Class 100 (lowest cost, US/EU only)
- **Staging**: Price Class 200 (moderate cost, most regions)
- **Production**: Price Class All (highest cost, global coverage)
- S3 lifecycle rules for log cleanup
- CloudFront caching reduces S3 requests

## Monitoring

- CloudFront access logs (optional, enabled in production)
- S3 bucket metrics
- CloudFront metrics (requests, data transfer, error rates)

## Troubleshooting

### Issue: 403 Forbidden

**Cause**: CloudFront OAI doesn't have permission to access S3 bucket

**Solution**: Verify bucket policy grants read access to OAI

### Issue: Stale Content After Deployment

**Cause**: CloudFront cache not invalidated

**Solution**: Create cache invalidation after deployment:
```bash
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

### Issue: Custom Domain Not Working

**Cause**: DNS not configured or certificate not valid

**Solution**: 
1. Verify ACM certificate is in `us-east-1` region
2. Verify CNAME record points to CloudFront distribution
3. Wait for DNS propagation (up to 48 hours)

## Related Stacks

- **API Stack**: Provides the backend API URL
- **Storage Stack**: Separate from frontend hosting (for processing results)
- **Monitoring Stack**: Monitors CloudFront and S3 metrics

## References

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront OAI](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
