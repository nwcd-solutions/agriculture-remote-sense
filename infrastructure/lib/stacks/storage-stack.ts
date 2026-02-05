import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface StorageStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
}

export class StorageStack extends cdk.Stack {
  public readonly resultsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StorageStackProps) {
    super(scope, id, props);

    const { config } = props;

    // Create S3 bucket for processing results
    this.resultsBucket = new s3.Bucket(this, 'ResultsBucket', {
      bucketName: `satellite-gis-results-${config.environment}-${config.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: config.environment !== 'prod',
      
      // Lifecycle rules for automatic cleanup
      lifecycleRules: [
        {
          id: 'DeleteOldResults',
          enabled: true,
          expiration: cdk.Duration.days(config.storage.resultsBucketLifecycleDays),
          prefix: 'tasks/',
          // Only add transition if expiration is significantly greater than transition period
          ...(config.storage.resultsBucketLifecycleDays > 14 ? {
            transitions: [
              {
                storageClass: s3.StorageClass.INTELLIGENT_TIERING,
                transitionAfter: cdk.Duration.days(7),
              },
            ],
          } : {}),
        },
        {
          id: 'DeleteTempFiles',
          enabled: true,
          expiration: cdk.Duration.days(config.storage.tempFilesLifecycleDays),
          prefix: 'temp/',
        },
        {
          id: 'DeleteLogs',
          enabled: true,
          expiration: cdk.Duration.days(config.monitoring.logRetentionDays),
          prefix: 'logs/',
        },
        {
          id: 'AbortIncompleteMultipartUpload',
          enabled: true,
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
        },
      ],

      // CORS configuration for frontend access
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.DELETE,
            s3.HttpMethods.HEAD,
          ],
          allowedOrigins: ['*'], // TODO: Restrict to specific domains in production
          allowedHeaders: ['*'],
          exposedHeaders: [
            'ETag',
            'Content-Length',
            'Content-Type',
            'x-amz-request-id',
          ],
          maxAge: 3000,
        },
      ],

      // Enable event notifications (for future Lambda triggers)
      eventBridgeEnabled: true,
    });

    // Output bucket name and ARN
    new cdk.CfnOutput(this, 'ResultsBucketName', {
      value: this.resultsBucket.bucketName,
      description: 'S3 bucket name for processing results',
      exportName: `SatelliteGis-ResultsBucket-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ResultsBucketArn', {
      value: this.resultsBucket.bucketArn,
      description: 'S3 bucket ARN for processing results',
      exportName: `SatelliteGis-ResultsBucketArn-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ResultsBucketDomainName', {
      value: this.resultsBucket.bucketDomainName,
      description: 'S3 bucket domain name',
      exportName: `SatelliteGis-ResultsBucketDomain-${config.environment}`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Storage');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
