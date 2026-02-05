import * as cdk from 'aws-cdk-lib';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface CicdStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiRepository: ecr.IRepository;
  batchRepository: ecr.IRepository;
  ecsClusterName?: string;
  ecsServiceName?: string;
}

export class CicdStack extends cdk.Stack {
  public readonly pipeline: codepipeline.Pipeline;
  public readonly apiBuildProject: codebuild.Project;
  public readonly batchBuildProject: codebuild.Project;

  constructor(scope: Construct, id: string, props: CicdStackProps) {
    super(scope, id, props);

    const { config, apiRepository, batchRepository } = props;

    // Create S3 bucket for pipeline artifacts
    const artifactBucket = new s3.Bucket(this, 'ArtifactBucket', {
      bucketName: `${config.projectName}-pipeline-artifacts-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [
        {
          id: 'DeleteOldArtifacts',
          enabled: true,
          expiration: cdk.Duration.days(30),
        },
      ],
    });

    // Create SNS topic for pipeline notifications
    const pipelineTopic = new sns.Topic(this, 'PipelineTopic', {
      topicName: `${config.projectName}-pipeline-notifications`,
      displayName: 'Satellite GIS Pipeline Notifications',
    });

    // Add email subscription if provided
    if (config.notificationEmail) {
      pipelineTopic.addSubscription(
        new subscriptions.EmailSubscription(config.notificationEmail)
      );
    }

    // Create CodeBuild project for API container
    this.apiBuildProject = new codebuild.Project(this, 'ApiBuildProject', {
      projectName: `${config.projectName}-api-build`,
      description: 'Build and push API Docker image to ECR',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        privileged: true, // Required for Docker builds
        computeType: codebuild.ComputeType.SMALL,
        environmentVariables: {
          AWS_ACCOUNT_ID: {
            value: this.account,
          },
          AWS_DEFAULT_REGION: {
            value: this.region,
          },
          ECR_REPOSITORY_URI: {
            value: apiRepository.repositoryUri,
          },
          IMAGE_TAG: {
            value: 'latest',
          },
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo Logging in to Amazon ECR...',
              'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
              'echo Build started on `date`',
            ],
          },
          build: {
            commands: [
              'echo Building the Docker image...',
              'cd backend',
              'docker build -t $ECR_REPOSITORY_URI:latest -f Dockerfile .',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG',
            ],
          },
          post_build: {
            commands: [
              'echo Build completed on `date`',
              'echo Pushing the Docker images...',
              'docker push $ECR_REPOSITORY_URI:latest',
              'docker push $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'echo Writing image definitions file...',
              'printf \'[{"name":"api","imageUri":"%s"}]\' $ECR_REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json',
              'cat imagedefinitions.json',
            ],
          },
        },
        artifacts: {
          files: ['backend/imagedefinitions.json'],
        },
      }),
      cache: codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER),
    });

    // Grant ECR permissions to API build project
    apiRepository.grantPullPush(this.apiBuildProject);

    // Create CodeBuild project for Batch container
    this.batchBuildProject = new codebuild.Project(this, 'BatchBuildProject', {
      projectName: `${config.projectName}-batch-build`,
      description: 'Build and push Batch processor Docker image to ECR',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        privileged: true,
        computeType: codebuild.ComputeType.SMALL,
        environmentVariables: {
          AWS_ACCOUNT_ID: {
            value: this.account,
          },
          AWS_DEFAULT_REGION: {
            value: this.region,
          },
          ECR_REPOSITORY_URI: {
            value: batchRepository.repositoryUri,
          },
          IMAGE_TAG: {
            value: 'latest',
          },
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo Logging in to Amazon ECR...',
              'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
              'echo Build started on `date`',
            ],
          },
          build: {
            commands: [
              'echo Building the Docker image...',
              'cd backend',
              'docker build -t $ECR_REPOSITORY_URI:latest -f Dockerfile.batch .',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG',
            ],
          },
          post_build: {
            commands: [
              'echo Build completed on `date`',
              'echo Pushing the Docker images...',
              'docker push $ECR_REPOSITORY_URI:latest',
              'docker push $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'echo Batch image pushed successfully',
            ],
          },
        },
      }),
      cache: codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER),
    });

    // Grant ECR permissions to Batch build project
    batchRepository.grantPullPush(this.batchBuildProject);

    // Create CodePipeline
    const sourceOutput = new codepipeline.Artifact('SourceOutput');
    const apiBuildOutput = new codepipeline.Artifact('ApiBuildOutput');

    this.pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: `${config.projectName}-pipeline`,
      artifactBucket: artifactBucket,
      restartExecutionOnUpdate: true,
    });

    // Source stage - GitHub or CodeCommit
    // Note: You'll need to configure this based on your source control
    // For now, using a manual trigger approach
    const sourceAction = new codepipeline_actions.CodeStarConnectionsSourceAction({
      actionName: 'GitHub_Source',
      owner: 'YOUR_GITHUB_USERNAME', // TODO: Replace with actual GitHub username
      repo: 'satellite-gis-platform', // TODO: Replace with actual repo name
      branch: config.environment === 'prod' ? 'main' : 'develop',
      output: sourceOutput,
      connectionArn: `arn:aws:codestar-connections:${this.region}:${this.account}:connection/YOUR_CONNECTION_ID`, // TODO: Replace with actual connection ARN
    });

    this.pipeline.addStage({
      stageName: 'Source',
      actions: [sourceAction],
    });

    // Build stage - Build both API and Batch containers in parallel
    this.pipeline.addStage({
      stageName: 'Build',
      actions: [
        new codepipeline_actions.CodeBuildAction({
          actionName: 'Build_API',
          project: this.apiBuildProject,
          input: sourceOutput,
          outputs: [apiBuildOutput],
        }),
        new codepipeline_actions.CodeBuildAction({
          actionName: 'Build_Batch',
          project: this.batchBuildProject,
          input: sourceOutput,
        }),
      ],
    });

    // Deploy stage - Update ECS service (if provided)
    if (props.ecsClusterName && props.ecsServiceName) {
      this.pipeline.addStage({
        stageName: 'Deploy',
        actions: [
          new codepipeline_actions.EcsDeployAction({
            actionName: 'Deploy_API',
            service: {
              clusterName: props.ecsClusterName,
              serviceName: props.ecsServiceName,
            } as any,
            input: apiBuildOutput,
          }),
        ],
      });
    }

    // Add pipeline notifications
    this.pipeline.onStateChange('PipelineStateChange', {
      target: new cdk.aws_events_targets.SnsTopic(pipelineTopic),
      description: 'Notify on pipeline state changes',
    });

    // Outputs
    new cdk.CfnOutput(this, 'PipelineName', {
      value: this.pipeline.pipelineName,
      description: 'CodePipeline name',
      exportName: `${config.projectName}-pipeline-name`,
    });

    new cdk.CfnOutput(this, 'ApiBuildProjectName', {
      value: this.apiBuildProject.projectName,
      description: 'API CodeBuild project name',
      exportName: `${config.projectName}-api-build-project`,
    });

    new cdk.CfnOutput(this, 'BatchBuildProjectName', {
      value: this.batchBuildProject.projectName,
      description: 'Batch CodeBuild project name',
      exportName: `${config.projectName}-batch-build-project`,
    });

    new cdk.CfnOutput(this, 'ArtifactBucketName', {
      value: artifactBucket.bucketName,
      description: 'Pipeline artifact bucket',
      exportName: `${config.projectName}-artifact-bucket`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'CicdStack');
    cdk.Tags.of(this).add('Environment', config.environment);
  }
}
