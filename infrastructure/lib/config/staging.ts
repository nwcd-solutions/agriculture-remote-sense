import { EnvironmentConfig } from './types';

export const stagingConfig: EnvironmentConfig = {
  environment: 'staging',
  account: process.env.CDK_DEFAULT_ACCOUNT || '',
  region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  projectName: 'satellite-gis',
  notificationEmail: process.env.NOTIFICATION_EMAIL,
  
  // VPC Configuration
  vpc: {
    maxAzs: 2,
    natGateways: 2,
  },
  
  // Batch Configuration
  batch: {
    computeEnvironment: {
      instanceTypes: ['m5.large', 'm5.xlarge', 'm5.2xlarge'],
      minvCpus: 0,
      maxvCpus: 32,
      desiredvCpus: 0,
      spotBidPercentage: 80,
    },
    jobQueue: {
      priority: 1,
    },
  },
  
  // API Configuration
  api: {
    cpu: 1024,
    memoryLimitMiB: 2048,
    desiredCount: 2,
    minCapacity: 2,
    maxCapacity: 6,
  },
  
  // Storage Configuration
  storage: {
    resultsBucketLifecycleDays: 14,
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
    logRetentionDays: 14,
    alarmEmail: process.env.ALARM_EMAIL || '',
  },
  
  // Frontend Configuration
  frontend: {
    domainName: undefined, // Optional custom domain
    certificateArn: undefined, // Optional ACM certificate ARN
    enableCloudFront: true,
    cloudFrontPriceClass: 'PriceClass_200', // US, Canada, Europe, Asia, Middle East, Africa
    branchName: 'staging',
    repositoryUrl: undefined,
    githubToken: undefined,
  },
  
  // Tags
  tags: {
    Environment: 'staging',
    Project: 'SatelliteGIS',
    ManagedBy: 'CDK',
  },
};
