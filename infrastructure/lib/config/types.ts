export interface EnvironmentConfig {
  environment: string;
  account: string;
  region: string;
  projectName: string;
  notificationEmail?: string;
  
  vpc: {
    maxAzs: number;
    natGateways: number;
  };
  
  batch: {
    computeEnvironment: {
      instanceTypes: string[];
      minvCpus: number;
      maxvCpus: number;
      desiredvCpus: number;
      spotBidPercentage: number;
    };
    jobQueue: {
      priority: number;
    };
  };
  
  api: {
    cpu: number;
    memoryLimitMiB: number;
    desiredCount: number;
    minCapacity: number;
    maxCapacity: number;
  };
  
  storage: {
    resultsBucketLifecycleDays: number;
    tempFilesLifecycleDays: number;
  };
  
  database: {
    tasksTableBillingMode: string;
    ttlEnabled: boolean;
    ttlAttributeName: string;
  };
  
  monitoring: {
    enableDetailedMonitoring: boolean;
    logRetentionDays: number;
    alarmEmail: string;
  };
  
  frontend: {
    domainName?: string;
    certificateArn?: string;
    enableCloudFront: boolean;
    cloudFrontPriceClass: string;
    branchName?: string;
    repositoryUrl?: string;
    githubToken?: string;
  };
  
  tags: {
    [key: string]: string;
  };
}
