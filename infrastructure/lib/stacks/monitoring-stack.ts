import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as batch from 'aws-cdk-lib/aws-batch';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface MonitoringStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiService?: ecs.FargateService;
  batchJobQueue?: batch.IJobQueue;
  tasksTable?: dynamodb.Table;
}

export class MonitoringStack extends cdk.Stack {
  public readonly alarmTopic: sns.Topic;
  public readonly dashboard: cloudwatch.Dashboard;

  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    // Create SNS topic for alarms
    this.alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: `satellite-gis-alarms-${props.config.environment}`,
      displayName: `Satellite GIS Platform Alarms (${props.config.environment})`,
    });

    // Add email subscription if configured
    if (props.config.monitoring.alarmEmail) {
      this.alarmTopic.addSubscription(
        new subscriptions.EmailSubscription(props.config.monitoring.alarmEmail)
      );
    }

    // Create CloudWatch Dashboard
    this.dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: `SatelliteGis-${props.config.environment}`,
    });

    // API Service Monitoring
    if (props.apiService) {
      this.addApiServiceMonitoring(props.apiService, props.config);
    }

    // Batch Job Queue Monitoring
    if (props.batchJobQueue) {
      this.addBatchMonitoring(props.batchJobQueue, props.config);
    }

    // DynamoDB Table Monitoring
    if (props.tasksTable) {
      this.addDatabaseMonitoring(props.tasksTable, props.config);
    }

    // Output the SNS topic ARN
    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: this.alarmTopic.topicArn,
      description: 'SNS topic ARN for alarms',
      exportName: `SatelliteGis-AlarmTopic-${props.config.environment}`,
    });

    // Output the dashboard URL
    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${this.dashboard.dashboardName}`,
      description: 'CloudWatch dashboard URL',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Monitoring');
    cdk.Tags.of(this).add('Component', 'Observability');
  }

  private addApiServiceMonitoring(service: ecs.FargateService, config: EnvironmentConfig) {
    // CPU Utilization Metric
    const cpuMetric = service.metricCpuUtilization({
      period: cdk.Duration.minutes(5),
      statistic: 'Average',
    });

    // Memory Utilization Metric
    const memoryMetric = service.metricMemoryUtilization({
      period: cdk.Duration.minutes(5),
      statistic: 'Average',
    });

    // Create CPU alarm
    const cpuAlarm = new cloudwatch.Alarm(this, 'ApiCpuAlarm', {
      alarmName: `satellite-gis-api-cpu-${config.environment}`,
      alarmDescription: 'API service CPU utilization is too high',
      metric: cpuMetric,
      threshold: 80,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    cpuAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

    // Create Memory alarm
    const memoryAlarm = new cloudwatch.Alarm(this, 'ApiMemoryAlarm', {
      alarmName: `satellite-gis-api-memory-${config.environment}`,
      alarmDescription: 'API service memory utilization is too high',
      metric: memoryMetric,
      threshold: 80,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    memoryAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

    // Add API metrics to dashboard
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Service - CPU & Memory',
        left: [cpuMetric],
        right: [memoryMetric],
        width: 12,
      })
    );

    // Task count metric
    const taskCountMetric = new cloudwatch.Metric({
      namespace: 'ECS/ContainerInsights',
      metricName: 'RunningTaskCount',
      dimensionsMap: {
        ServiceName: service.serviceName,
        ClusterName: service.cluster.clusterName,
      },
      period: cdk.Duration.minutes(5),
      statistic: 'Average',
    });

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Service - Running Tasks',
        left: [taskCountMetric],
        width: 12,
      })
    );
  }

  private addBatchMonitoring(jobQueue: batch.IJobQueue, config: EnvironmentConfig) {
    // Batch job metrics
    const submittedJobsMetric = new cloudwatch.Metric({
      namespace: 'AWS/Batch',
      metricName: 'JobsSubmitted',
      dimensionsMap: {
        JobQueue: jobQueue.jobQueueName,
      },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    const runningJobsMetric = new cloudwatch.Metric({
      namespace: 'AWS/Batch',
      metricName: 'JobsRunning',
      dimensionsMap: {
        JobQueue: jobQueue.jobQueueName,
      },
      period: cdk.Duration.minutes(5),
      statistic: 'Average',
    });

    const failedJobsMetric = new cloudwatch.Metric({
      namespace: 'AWS/Batch',
      metricName: 'JobsFailed',
      dimensionsMap: {
        JobQueue: jobQueue.jobQueueName,
      },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    const succeededJobsMetric = new cloudwatch.Metric({
      namespace: 'AWS/Batch',
      metricName: 'JobsSucceeded',
      dimensionsMap: {
        JobQueue: jobQueue.jobQueueName,
      },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    // Create alarm for failed jobs
    const failedJobsAlarm = new cloudwatch.Alarm(this, 'BatchFailedJobsAlarm', {
      alarmName: `satellite-gis-batch-failed-${config.environment}`,
      alarmDescription: 'Batch jobs are failing',
      metric: failedJobsMetric,
      threshold: 5,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    failedJobsAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

    // Add Batch metrics to dashboard
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Batch Jobs - Status',
        left: [submittedJobsMetric, runningJobsMetric],
        right: [succeededJobsMetric, failedJobsMetric],
        width: 12,
      })
    );
  }

  private addDatabaseMonitoring(table: dynamodb.Table, config: EnvironmentConfig) {
    // DynamoDB metrics
    const readCapacityMetric = table.metricConsumedReadCapacityUnits({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    const writeCapacityMetric = table.metricConsumedWriteCapacityUnits({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    const userErrorsMetric = table.metricUserErrors({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    const systemErrorsMetric = table.metricSystemErrorsForOperations({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
    });

    // Create alarm for user errors
    const userErrorsAlarm = new cloudwatch.Alarm(this, 'DynamoDbUserErrorsAlarm', {
      alarmName: `satellite-gis-dynamodb-errors-${config.environment}`,
      alarmDescription: 'DynamoDB user errors detected',
      metric: userErrorsMetric,
      threshold: 10,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    userErrorsAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

    // Add DynamoDB metrics to dashboard
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB - Capacity Units',
        left: [readCapacityMetric],
        right: [writeCapacityMetric],
        width: 12,
      })
    );

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB - Errors',
        left: [userErrorsMetric, systemErrorsMetric],
        width: 12,
      })
    );
  }
}
