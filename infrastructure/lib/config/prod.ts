import { EnvironmentConfig } from './types';

export const prodConfig: EnvironmentConfig = {
  environment: 'prod',
  account: process.env.CDK_DEFAULT_ACCOUNT || '',
  region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  projectName: 'satellite-gis',
  notificationEmail: process.env.NOTIFICATION_EMAIL,
  
  // VPC Configuration
  vpc: {
    maxAzs: 3,
    natGateways: 3,
  },
  
  // Batch Configuration
  batch: {
    computeEnvironment: {
      instanceTypes: ['m5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge'],
      minvCpus: 0,
      maxvCpus: 64,
      desiredvCpus: 0,
      spotBidPercentage: 70,
    },
    jobQueue: {
      priority: 1,
    },
  },
  
  // API Configuration
  api: {
    cpu: 2048,
    memoryLimitMiB: 4096,
    desiredCount: 3,
    minCapacity: 3,
    maxCapacity: 10,
  },
  
  // Storage Configuration
  storage: {
    resultsBucketLifecycleDays: 30,
    tempFilesLifecycleDays: 1,
  },
  
  // Database Configuration
  database: {
    tasksTableBillingMode: 'PAY_PER_REQUEST',
    ttlEnabled: true,
    ttlAttributeName: 'expiresAt',
  },
  
  // Monitoring Configuration
  monitoring: {
    enableDetailedMonitoring: true,
    logRetentionDays: 30,
    alarmEmail: process.env.ALARM_EMAIL || '',
  },
  
  // Frontend Configuration
  frontend: {
    domainName: undefined, // Optional custom domain (e.g., 'app.example.com')
    certificateArn: undefined, // Optional ACM certificate ARN for custom domain
    enableCloudFront: true,
    cloudFrontPriceClass: 'PriceClass_All', // All edge locations
    branchName: 'main',
    repositoryUrl: undefined,
    githubToken: undefined,
  },
  
  // Tags
  tags: {
    Environment: 'prod',
    Project: 'SatelliteGIS',
    ManagedBy: 'CDK',
  },
};
