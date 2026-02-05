import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface DatabaseStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
}

export class DatabaseStack extends cdk.Stack {
  public readonly tasksTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const { config } = props;

    // Create DynamoDB table for processing tasks
    this.tasksTable = new dynamodb.Table(this, 'ProcessingTasksTable', {
      tableName: `ProcessingTasks-${config.environment}`,
      partitionKey: {
        name: 'task_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: config.database.tasksTableBillingMode === 'PAY_PER_REQUEST'
        ? dynamodb.BillingMode.PAY_PER_REQUEST
        : dynamodb.BillingMode.PROVISIONED,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: config.environment === 'prod'
        ? { pointInTimeRecoveryEnabled: true }
        : undefined,
      timeToLiveAttribute: config.database.ttlEnabled
        ? config.database.ttlAttributeName
        : undefined,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
    });

    // Create GSI: Query by status
    this.tasksTable.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: {
        name: 'status',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Create GSI: Query by Batch Job ID
    this.tasksTable.addGlobalSecondaryIndex({
      indexName: 'BatchJobIndex',
      partitionKey: {
        name: 'batch_job_id',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Create GSI: Query by user (for future user authentication)
    this.tasksTable.addGlobalSecondaryIndex({
      indexName: 'UserIndex',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Output table name and ARN
    new cdk.CfnOutput(this, 'TasksTableName', {
      value: this.tasksTable.tableName,
      description: 'DynamoDB table name for processing tasks',
      exportName: `SatelliteGis-TasksTable-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'TasksTableArn', {
      value: this.tasksTable.tableArn,
      description: 'DynamoDB table ARN for processing tasks',
      exportName: `SatelliteGis-TasksTableArn-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'TasksTableStreamArn', {
      value: this.tasksTable.tableStreamArn || 'N/A',
      description: 'DynamoDB table stream ARN',
      exportName: `SatelliteGis-TasksTableStreamArn-${config.environment}`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Database');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
