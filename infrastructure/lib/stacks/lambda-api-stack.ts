import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
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
  public readonly restApi: apigateway.RestApi;
  public readonly apiUrl: string;
  public readonly apiKey: apigateway.IApiKey;

  constructor(scope: Construct, id: string, props: LambdaApiStackProps) {
    super(scope, id, props);

    const { config, tasksTable, resultsBucket, batchJobQueue, batchJobDefinition } = props;

    // Create CloudWatch log group for API Gateway
    const apiLogGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: `/aws/apigateway/satellite-gis-api-${config.environment}`,
      retention: config.monitoring.logRetentionDays,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
    });

    // Common Lambda layer with dependencies (only for process function)
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('../backend/lambda-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Boto3 for satellite GIS process Lambda',
    });

    // Query Lambda Function (no dependencies needed - uses only built-in urllib)
    const queryFunction = new lambda.Function(this, 'QueryFunction', {
      functionName: `satellite-gis-query-${config.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_query.handler',
      code: lambda.Code.fromAsset('../backend'),
      // No layers needed - uses only Python built-in libraries
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        ENVIRONMENT: config.environment,
        LOG_LEVEL: config.environment === 'prod' ? 'INFO' : 'DEBUG',
      },
    });

    // Process Lambda Function (needs boto3 for DynamoDB, Batch, S3)
    const processFunction = new lambda.Function(this, 'ProcessFunction', {
      functionName: `satellite-gis-process-${config.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_process.handler',
      code: lambda.Code.fromAsset('../backend'),
      layers: [dependenciesLayer], // Only process function needs the layer
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

    // AOI Lambda Function (no dependencies needed - uses only built-in libraries)
    const aoiFunction = new lambda.Function(this, 'AoiFunction', {
      functionName: `satellite-gis-aoi-${config.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_aoi.handler',
      code: lambda.Code.fromAsset('../backend'),
      // No layers needed - uses only Python built-in libraries
      memorySize: 256,
      timeout: cdk.Duration.seconds(15),
      environment: {
        ENVIRONMENT: config.environment,
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
        `${batchJobDefinition.jobDefinitionArn}:*`,  // Include all versions
        batchJobDefinition.jobDefinitionArn,
        `arn:aws:batch:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:job/*`,
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

    // Create REST API Gateway
    this.restApi = new apigateway.RestApi(this, 'RestApi', {
      restApiName: `satellite-gis-api-${config.environment}`,
      description: 'Satellite GIS REST API Gateway with Lambda',
      deployOptions: {
        stageName: config.environment,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(apiLogGroup),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields({
          caller: true,
          httpMethod: true,
          ip: true,
          protocol: true,
          requestTime: true,
          resourcePath: true,
          responseLength: true,
          status: true,
          user: true,
        }),
        throttlingRateLimit: 100,
        throttlingBurstLimit: 200,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
        allowCredentials: false,
      },
      cloudWatchRole: true,
    });

    // Create API Key
    this.apiKey = this.restApi.addApiKey('ApiKey', {
      apiKeyName: `satellite-gis-key-${config.environment}`,
      description: `API Key for Satellite GIS Platform (${config.environment})`,
    });

    // Create Usage Plan with rate limiting and quota
    const usagePlan = this.restApi.addUsagePlan('UsagePlan', {
      name: `satellite-gis-usage-${config.environment}`,
      description: `Usage plan for Satellite GIS Platform (${config.environment})`,
      throttle: {
        rateLimit: 100,  // requests per second
        burstLimit: 200, // maximum concurrent requests
      },
      quota: {
        limit: 10000,  // requests per day
        period: apigateway.Period.DAY,
      },
    });

    // Associate API key with usage plan
    usagePlan.addApiKey(this.apiKey);
    usagePlan.addApiStage({
      stage: this.restApi.deploymentStage,
    });

    // Create Lambda integrations
    const queryIntegration = new apigateway.LambdaIntegration(queryFunction, {
      proxy: true,
      allowTestInvoke: config.environment !== 'prod',
    });

    const processIntegration = new apigateway.LambdaIntegration(processFunction, {
      proxy: true,
      allowTestInvoke: config.environment !== 'prod',
    });

    const aoiIntegration = new apigateway.LambdaIntegration(aoiFunction, {
      proxy: true,
      allowTestInvoke: config.environment !== 'prod',
    });

    // Create /api resource
    const apiResource = this.restApi.root.addResource('api');

    // Create /api/query endpoint
    const queryResource = apiResource.addResource('query');
    queryResource.addMethod('POST', queryIntegration, {
      apiKeyRequired: true,
      requestValidator: new apigateway.RequestValidator(this, 'QueryRequestValidator', {
        restApi: this.restApi,
        requestValidatorName: 'query-validator',
        validateRequestBody: true,
        validateRequestParameters: false,
      }),
    });

    // Create /api/process resource
    const processResource = apiResource.addResource('process');

    // Create /api/process/indices endpoint
    const indicesResource = processResource.addResource('indices');
    indicesResource.addMethod('POST', processIntegration, {
      apiKeyRequired: true,
      requestValidator: new apigateway.RequestValidator(this, 'IndicesRequestValidator', {
        restApi: this.restApi,
        requestValidatorName: 'indices-validator',
        validateRequestBody: true,
        validateRequestParameters: false,
      }),
    });

    // Create /api/process/tasks/{task_id} endpoint
    const tasksResource = processResource.addResource('tasks');
    const taskIdResource = tasksResource.addResource('{task_id}');
    
    taskIdResource.addMethod('GET', processIntegration, {
      apiKeyRequired: true,
      requestParameters: {
        'method.request.path.task_id': true,
      },
    });

    taskIdResource.addMethod('DELETE', processIntegration, {
      apiKeyRequired: true,
      requestParameters: {
        'method.request.path.task_id': true,
      },
    });

    // Add GET method for listing all tasks
    tasksResource.addMethod('GET', processIntegration, {
      apiKeyRequired: true,
      requestParameters: {
        'method.request.querystring.status': false,
        'method.request.querystring.limit': false,
        'method.request.querystring.offset': false,
      },
    });

    // Create /api/aoi resource
    const aoiResource = apiResource.addResource('aoi');

    // Create /api/aoi/validate endpoint
    const validateResource = aoiResource.addResource('validate');
    validateResource.addMethod('POST', aoiIntegration, {
      apiKeyRequired: true,
      requestValidator: new apigateway.RequestValidator(this, 'AoiValidateRequestValidator', {
        restApi: this.restApi,
        requestValidatorName: 'aoi-validate-validator',
        validateRequestBody: true,
        validateRequestParameters: false,
      }),
    });

    // Create /api/aoi/upload endpoint
    const uploadResource = aoiResource.addResource('upload');
    uploadResource.addMethod('POST', aoiIntegration, {
      apiKeyRequired: true,
    });

    // Set API URL
    this.apiUrl = this.restApi.url;

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.apiUrl,
      description: 'REST API Gateway URL',
      exportName: `SatelliteGis-ApiUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ApiKeyId', {
      value: this.apiKey.keyId,
      description: 'API Key ID',
      exportName: `SatelliteGis-ApiKeyId-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ApiKeyArn', {
      value: this.apiKey.keyArn,
      description: 'API Key ARN',
    });

    new cdk.CfnOutput(this, 'QueryFunctionName', {
      value: queryFunction.functionName,
      description: 'Query Lambda function name',
    });

    new cdk.CfnOutput(this, 'ProcessFunctionName', {
      value: processFunction.functionName,
      description: 'Process Lambda function name',
    });

    new cdk.CfnOutput(this, 'AoiFunctionName', {
      value: aoiFunction.functionName,
      description: 'AOI Lambda function name',
    });

    new cdk.CfnOutput(this, 'UsagePlanId', {
      value: usagePlan.usagePlanId,
      description: 'API Usage Plan ID',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'LambdaAPI');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }
}
