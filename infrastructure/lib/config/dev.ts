import { EnvironmentConfig } from './types';

export const devConfig: EnvironmentConfig = {
  environment: 'dev',
  account: process.env.CDK_DEFAULT_ACCOUNT || '',
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  projectName: 'satellite-gis',
  notificationEmail: process.env.NOTIFICATION_EMAIL,
  
  // VPC Configuration
  vpc: {
    maxAzs: 2,
    natGateways: 1,
  },
  
  // Batch Configuration
  batch: {
    computeEnvironment: {
      instanceTypes: ['m5.large', 'm5.xlarge'],
      minvCpus: 0,
      maxvCpus: 16,
      desiredvCpus: 0,
      spotBidPercentage: 80,
    },
    jobQueue: {
      priority: 1,
    },
  },
  
  // API Configuration
  api: {
    cpu: 512,
    memoryLimitMiB: 1024,
    desiredCount: 1,
    minCapacity: 1,
    maxCapacity: 3,
  },
  
  // Storage Configuration
  storage: {
    resultsBucketLifecycleDays: 7,
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
    logRetentionDays: 7,
    alarmEmail: process.env.ALARM_EMAIL || '',
  },
  
  // Frontend Configuration
  frontend: {
    domainName: undefined, // Optional custom domain
    certificateArn: undefined, // Optional ACM certificate ARN
    enableCloudFront: true,
    cloudFrontPriceClass: 'PriceClass_100', // US, Canada, Europe
    branchName: 'main', // Git branch name for Amplify
    repositoryUrl: 'https://github.com/nwcd-solutions/agriculture-remote-sense', // GitHub repo URL (public)
    githubToken: process.env.GITHUB_TOKEN, // GitHub access token (set via environment variable)
  },
  
  // Tags
  tags: {
    Environment: 'dev',
    Project: 'SatelliteGIS',
    ManagedBy: 'CDK',
  },
};
