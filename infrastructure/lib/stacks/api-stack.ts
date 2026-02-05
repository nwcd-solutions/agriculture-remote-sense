import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigatewayv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as batch from 'aws-cdk-lib/aws-batch';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface ApiStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
  tasksTable: dynamodb.Table;
  resultsBucket: s3.Bucket;
  batchJobQueue: batch.JobQueue;
  batchJobDefinition: batch.EcsJobDefinition;
}

export class ApiStack extends cdk.Stack {
  public readonly service: ecs.FargateService;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly httpApi: apigatewayv2.HttpApi;
  public readonly apiUrl: string;
  public readonly apiGatewayUrl: string;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const { config, vpc, securityGroup, tasksTable, resultsBucket, batchJobQueue, batchJobDefinition } = props;

    // Build container image from source
    const containerImage = ecs.ContainerImage.fromAsset('../backend', {
      file: 'Dockerfile',
      platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
    });

    // Create ECS cluster
    const cluster = new ecs.Cluster(this, 'ApiCluster', {
      clusterName: `satellite-gis-api-${config.environment}`,
      vpc,
      containerInsights: config.monitoring.enableDetailedMonitoring,
    });

    // Create IAM role for ECS task execution
    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Create IAM role for ECS task (application role)
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'IAM role for API service tasks',
    });

    // Grant DynamoDB permissions
    tasksTable.grantReadWriteData(taskRole);

    // Grant S3 permissions
    resultsBucket.grantReadWrite(taskRole);

    // Grant Batch permissions
    taskRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'batch:SubmitJob',
        'batch:DescribeJobs',
        'batch:TerminateJob',
        'batch:ListJobs',
      ],
      resources: [
        batchJobQueue.jobQueueArn,
        batchJobDefinition.jobDefinitionArn,
        `arn:aws:batch:${this.region}:${this.account}:job/*`,
      ],
    }));

    // Grant access to read from AWS Open Data (public S3 buckets)
    taskRole.addToPolicy(new iam.PolicyStatement({
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

    // Create CloudWatch log group
    const logGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: `/ecs/satellite-gis-api-${config.environment}`,
      retention: config.monitoring.logRetentionDays,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
    });

    // Create Fargate task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDefinition', {
      family: `satellite-gis-api-${config.environment}`,
      cpu: config.api.cpu,
      memoryLimitMiB: config.api.memoryLimitMiB,
      executionRole,
      taskRole,
    });

    // Add container to task definition
    const container = taskDefinition.addContainer('ApiContainer', {
      containerName: 'api',
      image: containerImage,  // Use the container image built from source
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: 'api',
        logGroup,
      }),
      environment: {
        ENVIRONMENT: config.environment,
        AWS_REGION: this.region,
        DYNAMODB_TABLE: tasksTable.tableName,
        S3_BUCKET: resultsBucket.bucketName,
        BATCH_JOB_QUEUE: batchJobQueue.jobQueueName,
        BATCH_JOB_DEFINITION: batchJobDefinition.jobDefinitionName,
        PYTHONUNBUFFERED: '1',
        LOG_LEVEL: config.environment === 'prod' ? 'INFO' : 'DEBUG',
        CORS_ORIGINS: 'http://localhost:3000,https://dev.dfjse3jyewuby.amplifyapp.com,https://main.dfjse3jyewuby.amplifyapp.com',
      },
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    // Expose port 8000
    container.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    // Create Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, 'LoadBalancer', {
      loadBalancerName: `satellite-gis-alb-${config.environment}`,
      vpc,
      internetFacing: true,
      securityGroup,
    });

    // Create target group
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'TargetGroup', {
      targetGroupName: `satellite-gis-tg-${config.environment}`,
      vpc,
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
      deregistrationDelay: cdk.Duration.seconds(30),
    });

    // Add HTTP listener
    const httpListener = this.loadBalancer.addListener('HttpListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [targetGroup],
    });

    // Create Fargate service
    this.service = new ecs.FargateService(this, 'Service', {
      serviceName: `satellite-gis-api-${config.environment}`,
      cluster,
      taskDefinition,
      desiredCount: config.api.desiredCount,
      minHealthyPercent: 50,
      maxHealthyPercent: 200,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [securityGroup],
      assignPublicIp: false,
      enableExecuteCommand: config.environment !== 'prod',
      circuitBreaker: {
        rollback: true,
      },
    });

    // Attach service to target group
    this.service.attachToApplicationTargetGroup(targetGroup);

    // Configure auto-scaling
    const scaling = this.service.autoScaleTaskCount({
      minCapacity: config.api.minCapacity,
      maxCapacity: config.api.maxCapacity,
    });

    // Scale based on CPU utilization
    scaling.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Scale based on memory utilization
    scaling.scaleOnMemoryUtilization('MemoryScaling', {
      targetUtilizationPercent: 80,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Scale based on request count
    scaling.scaleOnRequestCount('RequestScaling', {
      requestsPerTarget: 1000,
      targetGroup,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Set API URL
    this.apiUrl = `http://${this.loadBalancer.loadBalancerDnsName}`;

    // Outputs
    new cdk.CfnOutput(this, 'LoadBalancerDnsName', {
      value: this.loadBalancer.loadBalancerDnsName,
      description: 'Application Load Balancer DNS name',
      exportName: `SatelliteGis-ApiUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.apiUrl,
      description: 'API base URL',
      exportName: `SatelliteGis-ApiBaseUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ServiceName', {
      value: this.service.serviceName,
      description: 'ECS service name',
      exportName: `SatelliteGis-ApiServiceName-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'ECS cluster name',
      exportName: `SatelliteGis-ApiClusterName-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'LogGroupName', {
      value: logGroup.logGroupName,
      description: 'CloudWatch log group name',
      exportName: `SatelliteGis-ApiLogGroup-${config.environment}`,
    });

    // Create VPC Link for API Gateway
    const vpcLink = new apigatewayv2.VpcLink(this, 'VpcLink', {
      vpc,
      vpcLinkName: `satellite-gis-vpclink-${config.environment}`,
      subnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [securityGroup],
    });

    // Create HTTP API Gateway
    this.httpApi = new apigatewayv2.HttpApi(this, 'HttpApi', {
      apiName: `satellite-gis-api-${config.environment}`,
      description: 'Satellite GIS API Gateway',
      corsPreflight: {
        allowOrigins: [
          'http://localhost:3000',
          'https://dev.dfjse3jyewuby.amplifyapp.com',
          'https://main.dfjse3jyewuby.amplifyapp.com',
        ],
        allowMethods: [
          apigatewayv2.CorsHttpMethod.GET,
          apigatewayv2.CorsHttpMethod.POST,
          apigatewayv2.CorsHttpMethod.PUT,
          apigatewayv2.CorsHttpMethod.DELETE,
          apigatewayv2.CorsHttpMethod.OPTIONS,
        ],
        allowHeaders: ['*'],
        allowCredentials: false,
      },
    });

    // Create HTTP integration with ALB via VPC Link
    const albIntegration = new apigatewayv2_integrations.HttpAlbIntegration(
      'AlbIntegration',
      httpListener,
      {
        vpcLink,
      }
    );

    // Add catch-all route
    this.httpApi.addRoutes({
      path: '/{proxy+}',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: albIntegration,
    });

    // Add root route
    this.httpApi.addRoutes({
      path: '/',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: albIntegration,
    });

    // Set API Gateway URL
    this.apiGatewayUrl = this.httpApi.apiEndpoint;

    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: this.apiGatewayUrl,
      description: 'API Gateway HTTPS URL',
      exportName: `SatelliteGis-ApiGatewayUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'VpcLinkId', {
      value: vpcLink.vpcLinkId,
      description: 'VPC Link ID',
      exportName: `SatelliteGis-VpcLinkId-${config.environment}`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'API');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
