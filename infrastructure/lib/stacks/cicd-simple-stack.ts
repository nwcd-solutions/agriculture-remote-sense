import * as cdk from 'aws-cdk-lib';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface CicdSimpleStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiRepository: ecr.IRepository;
  batchRepository: ecr.IRepository;
}

/**
 * Simple CI/CD Stack for building and pushing Docker images
 * This stack creates CodeBuild projects that can be triggered manually or via webhooks
 */
export class CicdSimpleStack extends cdk.Stack {
  public readonly apiBuildProject: codebuild.Project;
  public readonly batchBuildProject: codebuild.Project;
  public readonly combinedBuildProject: codebuild.Project;

  constructor(scope: Construct, id: string, props: CicdSimpleStackProps) {
    super(scope, id, props);

    const { config, apiRepository, batchRepository } = props;

    // Create SNS topic for build notifications
    const buildTopic = new sns.Topic(this, 'BuildNotificationTopic', {
      topicName: `${config.projectName}-build-notifications`,
      displayName: 'Satellite GIS Build Notifications',
    });

    // Add email subscription if provided
    if (config.notificationEmail) {
      buildTopic.addSubscription(
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
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo "========================================="',
              'echo "Building API Container"',
              'echo "========================================="',
              'echo "Logging in to Amazon ECR..."',
              'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
              'BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
              'echo "Image tag: $IMAGE_TAG"',
              'echo "Build started at: $BUILD_DATE"',
            ],
          },
          build: {
            commands: [
              'echo "Building the Docker image..."',
              'cd backend',
              'docker build -t $ECR_REPOSITORY_URI:latest -f Dockerfile .',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
            ],
          },
          post_build: {
            commands: [
              'echo "Build completed successfully"',
              'echo "Pushing the Docker images..."',
              'docker push $ECR_REPOSITORY_URI:latest',
              'docker push $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker push $ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "========================================="',
              'echo "API Image pushed successfully!"',
              'echo "Repository: $ECR_REPOSITORY_URI"',
              'echo "Tags: latest, $IMAGE_TAG, build-$CODEBUILD_BUILD_NUMBER"',
              'echo "========================================="',
            ],
          },
        },
      }),
      cache: codebuild.Cache.local(
        codebuild.LocalCacheMode.DOCKER_LAYER,
        codebuild.LocalCacheMode.SOURCE
      ),
      timeout: cdk.Duration.minutes(30),
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
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo "========================================="',
              'echo "Building Batch Processor Container"',
              'echo "========================================="',
              'echo "Logging in to Amazon ECR..."',
              'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
              'BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
              'echo "Image tag: $IMAGE_TAG"',
              'echo "Build started at: $BUILD_DATE"',
            ],
          },
          build: {
            commands: [
              'echo "Building the Docker image..."',
              'cd backend',
              'docker build -t $ECR_REPOSITORY_URI:latest -f Dockerfile.batch .',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
            ],
          },
          post_build: {
            commands: [
              'echo "Build completed successfully"',
              'echo "Pushing the Docker images..."',
              'docker push $ECR_REPOSITORY_URI:latest',
              'docker push $ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker push $ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "========================================="',
              'echo "Batch Image pushed successfully!"',
              'echo "Repository: $ECR_REPOSITORY_URI"',
              'echo "Tags: latest, $IMAGE_TAG, build-$CODEBUILD_BUILD_NUMBER"',
              'echo "========================================="',
            ],
          },
        },
      }),
      cache: codebuild.Cache.local(
        codebuild.LocalCacheMode.DOCKER_LAYER,
        codebuild.LocalCacheMode.SOURCE
      ),
      timeout: cdk.Duration.minutes(30),
    });

    // Grant ECR permissions to Batch build project
    batchRepository.grantPullPush(this.batchBuildProject);

    // Create combined build project that builds both containers
    this.combinedBuildProject = new codebuild.Project(this, 'CombinedBuildProject', {
      projectName: `${config.projectName}-combined-build`,
      description: 'Build and push both API and Batch Docker images to ECR',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        privileged: true,
        computeType: codebuild.ComputeType.MEDIUM,
        environmentVariables: {
          AWS_ACCOUNT_ID: {
            value: this.account,
          },
          AWS_DEFAULT_REGION: {
            value: this.region,
          },
          API_ECR_REPOSITORY_URI: {
            value: apiRepository.repositoryUri,
          },
          BATCH_ECR_REPOSITORY_URI: {
            value: batchRepository.repositoryUri,
          },
        },
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          pre_build: {
            commands: [
              'echo "========================================="',
              'echo "Building Both API and Batch Containers"',
              'echo "========================================="',
              'echo "Logging in to Amazon ECR..."',
              'aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $API_ECR_REPOSITORY_URI',
              'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
              'IMAGE_TAG=${COMMIT_HASH:=latest}',
              'BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
              'echo "Image tag: $IMAGE_TAG"',
              'echo "Build started at: $BUILD_DATE"',
            ],
          },
          build: {
            commands: [
              'echo "========================================="',
              'echo "Building API Container..."',
              'echo "========================================="',
              'cd backend',
              'docker build -t $API_ECR_REPOSITORY_URI:latest -f Dockerfile .',
              'docker tag $API_ECR_REPOSITORY_URI:latest $API_ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker tag $API_ECR_REPOSITORY_URI:latest $API_ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "API container built successfully"',
              '',
              'echo "========================================="',
              'echo "Building Batch Container..."',
              'echo "========================================="',
              'docker build -t $BATCH_ECR_REPOSITORY_URI:latest -f Dockerfile.batch .',
              'docker tag $BATCH_ECR_REPOSITORY_URI:latest $BATCH_ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker tag $BATCH_ECR_REPOSITORY_URI:latest $BATCH_ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "Batch container built successfully"',
            ],
          },
          post_build: {
            commands: [
              'echo "========================================="',
              'echo "Pushing API Images..."',
              'echo "========================================="',
              'docker push $API_ECR_REPOSITORY_URI:latest',
              'docker push $API_ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker push $API_ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "API images pushed successfully"',
              '',
              'echo "========================================="',
              'echo "Pushing Batch Images..."',
              'echo "========================================="',
              'docker push $BATCH_ECR_REPOSITORY_URI:latest',
              'docker push $BATCH_ECR_REPOSITORY_URI:$IMAGE_TAG',
              'docker push $BATCH_ECR_REPOSITORY_URI:build-$CODEBUILD_BUILD_NUMBER',
              'echo "Batch images pushed successfully"',
              '',
              'echo "========================================="',
              'echo "Build Complete!"',
              'echo "========================================="',
              'echo "API Repository: $API_ECR_REPOSITORY_URI"',
              'echo "Batch Repository: $BATCH_ECR_REPOSITORY_URI"',
              'echo "Tags: latest, $IMAGE_TAG, build-$CODEBUILD_BUILD_NUMBER"',
              'echo "========================================="',
            ],
          },
        },
      }),
      cache: codebuild.Cache.local(
        codebuild.LocalCacheMode.DOCKER_LAYER,
        codebuild.LocalCacheMode.SOURCE
      ),
      timeout: cdk.Duration.minutes(60),
    });

    // Grant ECR permissions to combined build project
    apiRepository.grantPullPush(this.combinedBuildProject);
    batchRepository.grantPullPush(this.combinedBuildProject);

    // Add build notifications
    this.apiBuildProject.onBuildFailed('ApiBuildFailed', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when API build fails',
    });

    this.apiBuildProject.onBuildSucceeded('ApiBuildSucceeded', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when API build succeeds',
    });

    this.batchBuildProject.onBuildFailed('BatchBuildFailed', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when Batch build fails',
    });

    this.batchBuildProject.onBuildSucceeded('BatchBuildSucceeded', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when Batch build succeeds',
    });

    this.combinedBuildProject.onBuildFailed('CombinedBuildFailed', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when combined build fails',
    });

    this.combinedBuildProject.onBuildSucceeded('CombinedBuildSucceeded', {
      target: new targets.SnsTopic(buildTopic),
      description: 'Notify when combined build succeeds',
    });

    // Outputs
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

    new cdk.CfnOutput(this, 'CombinedBuildProjectName', {
      value: this.combinedBuildProject.projectName,
      description: 'Combined CodeBuild project name (builds both)',
      exportName: `${config.projectName}-combined-build-project`,
    });

    new cdk.CfnOutput(this, 'ApiBuildProjectArn', {
      value: this.apiBuildProject.projectArn,
      description: 'API CodeBuild project ARN',
    });

    new cdk.CfnOutput(this, 'BatchBuildProjectArn', {
      value: this.batchBuildProject.projectArn,
      description: 'Batch CodeBuild project ARN',
    });

    new cdk.CfnOutput(this, 'BuildNotificationTopicArn', {
      value: buildTopic.topicArn,
      description: 'SNS topic for build notifications',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'CicdSimpleStack');
    cdk.Tags.of(this).add('Environment', config.environment);
  }
}
