import * as cdk from 'aws-cdk-lib';
import * as batch from 'aws-cdk-lib/aws-batch';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface BatchStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
  resultsBucket: s3.Bucket;
  tasksTable: dynamodb.Table;
}

export class BatchStack extends cdk.Stack {
  public readonly jobQueue: batch.JobQueue;
  public readonly jobDefinition: batch.EcsJobDefinition;
  public readonly computeEnvironment: batch.ManagedEc2EcsComputeEnvironment;

  constructor(scope: Construct, id: string, props: BatchStackProps) {
    super(scope, id, props);

    const { config, vpc, securityGroup, resultsBucket, tasksTable } = props;

    // Build container image from source
    const containerImage = ecs.ContainerImage.fromAsset('../backend', {
      file: 'batch/Dockerfile',
      platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
    });

    // Create IAM role for Batch job execution
    const jobRole = new iam.Role(this, 'BatchJobRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'IAM role for AWS Batch job execution',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
      ],
    });

    // Grant S3 read/write permissions to job role
    resultsBucket.grantReadWrite(jobRole);

    // Grant DynamoDB read/write permissions to job role
    tasksTable.grantReadWriteData(jobRole);

    // Grant access to read from AWS Open Data (public S3 buckets)
    jobRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
      ],
      resources: [
        'arn:aws:s3:::sentinel-*',
        'arn:aws:s3:::sentinel-*/*',
        'arn:aws:s3:::usgs-landsat',
        'arn:aws:s3:::usgs-landsat/*',
        'arn:aws:s3:::modis-*',
        'arn:aws:s3:::modis-*/*',
      ],
    }));

    // Create IAM role for Batch compute environment
    const instanceRole = new iam.Role(this, 'BatchInstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonEC2ContainerServiceforEC2Role'),
      ],
    });

    // Create Batch compute environment with Spot instances
    this.computeEnvironment = new batch.ManagedEc2EcsComputeEnvironment(
      this,
      'ComputeEnvironment',
      {
        computeEnvironmentName: `satellite-gis-compute-${config.environment}`,
        vpc,
        vpcSubnets: {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        securityGroups: [securityGroup],
        instanceTypes: config.batch.computeEnvironment.instanceTypes.map(
          (type) => new ec2.InstanceType(type)
        ),
        spot: true,
        spotBidPercentage: config.batch.computeEnvironment.spotBidPercentage,
        minvCpus: config.batch.computeEnvironment.minvCpus,
        maxvCpus: config.batch.computeEnvironment.maxvCpus,
        instanceRole,
        enabled: true,
        replaceComputeEnvironment: false,
      }
    );

    // Create Batch job queue
    this.jobQueue = new batch.JobQueue(this, 'JobQueue', {
      jobQueueName: `satellite-gis-queue-${config.environment}`,
      priority: config.batch.jobQueue.priority,
      computeEnvironments: [
        {
          computeEnvironment: this.computeEnvironment,
          order: 1,
        },
      ],
      enabled: true,
    });

    // Create Batch job definition
    this.jobDefinition = new batch.EcsJobDefinition(this, 'JobDefinition', {
      jobDefinitionName: `satellite-gis-processor-${config.environment}`,
      container: new batch.EcsEc2ContainerDefinition(this, 'Container', {
        image: containerImage,  // Use the container image built from source
        cpu: 4,
        memory: cdk.Size.mebibytes(8192),
        jobRole,
        environment: {
          S3_BUCKET: resultsBucket.bucketName,
          AWS_REGION: this.region,
          DYNAMODB_TABLE: tasksTable.tableName,
          ENVIRONMENT: config.environment,
          GDAL_CACHEMAX: '512',
          GDAL_HTTP_TIMEOUT: '600',
          PYTHONUNBUFFERED: '1',
        },
        logging: ecs.LogDriver.awsLogs({
          streamPrefix: 'batch-processor',
          logRetention: config.monitoring.logRetentionDays,
        }),
      }),
      retryAttempts: 3,
      timeout: cdk.Duration.hours(1),
    });

    // Outputs
    new cdk.CfnOutput(this, 'JobQueueArn', {
      value: this.jobQueue.jobQueueArn,
      description: 'AWS Batch job queue ARN',
    });

    new cdk.CfnOutput(this, 'JobQueueName', {
      value: this.jobQueue.jobQueueName,
      description: 'AWS Batch job queue name',
    });

    new cdk.CfnOutput(this, 'JobDefinitionArn', {
      value: this.jobDefinition.jobDefinitionArn,
      description: 'AWS Batch job definition ARN',
    });

    new cdk.CfnOutput(this, 'ComputeEnvironmentArn', {
      value: this.computeEnvironment.computeEnvironmentArn,
      description: 'AWS Batch compute environment ARN',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Batch');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
