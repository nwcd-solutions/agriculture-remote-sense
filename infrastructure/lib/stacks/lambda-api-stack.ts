import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigatewayv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as batch from 'aws-cdk-lib/aws-batch';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface LambdaApiStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  tasksTable: dynamodb.Table;
  resultsBucket: s3.Bucket;
  batchJobQueue: batch.JobQueue;
  batchJobDefinition: batch.EcsJobDefinition;
}

export class LambdaApiStack extends cdk.Stack {
  public readonly httpApi: apigatewayv2.HttpApi;
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: LambdaApiStackProps) {
    super(scope, id, props);

    const { config, tasksTable, resultsBucket, batchJobQueue, batchJobDefinition } = props;

    // Common Lambda layer with dependencies
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('../backend/lambda-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Dependencies for satellite GIS API',
    });

    // Query Lambda Function
    const queryFunction = new lambda.Function(this, 'QueryFunction', {
      functionName: `satellite-gis-query-${config.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_query.handler',
      code: lambda.Code.fromAsset('../backend'),
      layers: [dependenciesLayer],
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        ENVIRONMENT: config.environment,
        LOG_LEVEL: config.environment === 'prod' ? 'INFO' : 'DEBUG',
      },
    });

    // Process Lambda Function
    const processFunction = new lambda.Function(this, 'ProcessFunction', {
      functionName: `satellite-gis-process-${config.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_process.handler',
      code: lambda.Code.fromAsset('../backend'),
      layers: [dependenciesLayer],
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        ENVIRONMENT: config.environment,
        DYNAMODB_TABLE: tasksTable.tableName,
        S3_BUCKET: resultsBucket.bucketName,
        BATCH_JOB_QUEUE: batchJobQueue.jobQueueName,
        BATCH_JOB_DEFINITION: batchJobDefinition.jobDefinitionName,
        LOG_LEVEL: config.environment === 'prod' ? 'INFO' : 'DEBUG',
      },
    });

    // Grant permissions to process function
    tasksTable.grantReadWriteData(processFunction);
    resultsBucket.grantReadWrite(processFunction);

    processFunction.addToRolePolicy(new iam.PolicyStatement({
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

    // Grant access to AWS Open Data
    queryFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:GetObject', 's3:ListBucket'],
      resources: [
        'arn:aws:s3:::sentinel-*',
        'arn:aws:s3:::sentinel-*/*',
      ],
    }));

    // Create HTTP API Gateway
    this.httpApi = new apigatewayv2.HttpApi(this, 'HttpApi', {
      apiName: `satellite-gis-api-${config.environment}`,
      description: 'Satellite GIS API Gateway with Lambda',
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

    // Create integrations
    const queryIntegration = new apigatewayv2_integrations.HttpLambdaIntegration(
      'QueryIntegration',
      queryFunction
    );

    const processIntegration = new apigatewayv2_integrations.HttpLambdaIntegration(
      'ProcessIntegration',
      processFunction
    );

    // Add routes
    this.httpApi.addRoutes({
      path: '/api/query',
      methods: [apigatewayv2.HttpMethod.POST],
      integration: queryIntegration,
    });

    this.httpApi.addRoutes({
      path: '/api/process/indices',
      methods: [apigatewayv2.HttpMethod.POST],
      integration: processIntegration,
    });

    this.httpApi.addRoutes({
      path: '/api/process/tasks/{task_id}',
      methods: [apigatewayv2.HttpMethod.GET, apigatewayv2.HttpMethod.DELETE],
      integration: processIntegration,
    });

    // Set API URL
    this.apiUrl = this.httpApi.apiEndpoint;

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.apiUrl,
      description: 'API Gateway HTTPS URL',
      exportName: `SatelliteGis-ApiUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'QueryFunctionName', {
      value: queryFunction.functionName,
      description: 'Query Lambda function name',
    });

    new cdk.CfnOutput(this, 'ProcessFunctionName', {
      value: processFunction.functionName,
      description: 'Process Lambda function name',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'LambdaAPI');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
