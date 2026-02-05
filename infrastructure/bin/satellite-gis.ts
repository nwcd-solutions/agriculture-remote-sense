#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/network-stack';
import { StorageStack } from '../lib/stacks/storage-stack';
import { DatabaseStack } from '../lib/stacks/database-stack';
import { BatchStack } from '../lib/stacks/batch-stack';
import { LambdaApiStack } from '../lib/stacks/lambda-api-stack';
import { FrontendStack } from '../lib/stacks/frontend-stack';
import { MonitoringStack } from '../lib/stacks/monitoring-stack';
import { getConfig } from '../lib/config';

const app = new cdk.App();

// Get environment from context or environment variable
const environment = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const config = getConfig(environment);

// Ensure account and region are set
const env = {
  account: config.account || process.env.CDK_DEFAULT_ACCOUNT,
  region: config.region || process.env.CDK_DEFAULT_REGION || 'us-west-2',
};

// Create Network Stack
const networkStack = new NetworkStack(app, `SatelliteGis-Network-${config.environment}`, {
  env,
  config,
  description: `Network infrastructure for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Network-${config.environment}`,
});

// Create Storage Stack
const storageStack = new StorageStack(app, `SatelliteGis-Storage-${config.environment}`, {
  env,
  config,
  description: `Storage infrastructure for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Storage-${config.environment}`,
});

// Create Database Stack
const databaseStack = new DatabaseStack(app, `SatelliteGis-Database-${config.environment}`, {
  env,
  config,
  description: `Database infrastructure for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Database-${config.environment}`,
});

// Create Batch Stack - builds container from source
const batchStack = new BatchStack(app, `SatelliteGis-Batch-${config.environment}`, {
  env,
  config,
  description: `AWS Batch compute infrastructure for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Batch-${config.environment}`,
  vpc: networkStack.vpc,
  securityGroup: networkStack.batchSecurityGroup,
  resultsBucket: storageStack.resultsBucket,
  tasksTable: databaseStack.tasksTable,
});

// Create Lambda API Stack
const apiStack = new LambdaApiStack(app, `SatelliteGis-Api-${config.environment}`, {
  env,
  config,
  description: `Lambda API service for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Api-${config.environment}`,
  tasksTable: databaseStack.tasksTable,
  resultsBucket: storageStack.resultsBucket,
  batchJobQueue: batchStack.jobQueue,
  batchJobDefinition: batchStack.jobDefinition,
});

// Create Frontend Stack
const frontendStack = new FrontendStack(app, `SatelliteGis-Frontend-${config.environment}`, {
  env,
  config,
  description: `Frontend infrastructure for Satellite GIS Platform (${config.environment})`,
  stackName: `SatelliteGis-Frontend-${config.environment}`,
  apiUrl: apiStack.apiUrl,
  apiKeyId: apiStack.apiKey.keyId,
});

// Create Monitoring Stack (skip for now - Lambda doesn't have ECS service)
// const monitoringStack = new MonitoringStack(app, `SatelliteGis-Monitoring-${config.environment}`, {
//   env,
//   config,
//   description: `Monitoring infrastructure for Satellite GIS Platform (${config.environment})`,
//   stackName: `SatelliteGis-Monitoring-${config.environment}`,
//   batchJobQueue: batchStack.jobQueue,
//   tasksTable: databaseStack.tasksTable,
// });

// Apply tags to all stacks
Object.entries(config.tags).forEach(([key, value]) => {
  cdk.Tags.of(app).add(key, value);
});

app.synth();
