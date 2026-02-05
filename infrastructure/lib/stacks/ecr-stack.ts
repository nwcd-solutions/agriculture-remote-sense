import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface EcrStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
}

/**
 * ECR Stack - Creates container repositories for API and Batch
 * This stack must be deployed first before API, Batch, and CI/CD stacks
 */
export class EcrStack extends cdk.Stack {
  public readonly apiRepository: ecr.Repository;
  public readonly batchRepository: ecr.Repository;

  constructor(scope: Construct, id: string, props: EcrStackProps) {
    super(scope, id, props);

    const { config } = props;

    // Create ECR repository for API container
    this.apiRepository = new ecr.Repository(this, 'ApiRepository', {
      repositoryName: `${config.projectName}-api-${config.environment}`,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      lifecycleRules: [
        {
          description: 'Keep only last 10 images',
          maxImageCount: 10,
          rulePriority: 1,
        },
      ],
    });

    // Create ECR repository for Batch processing container
    this.batchRepository = new ecr.Repository(this, 'BatchRepository', {
      repositoryName: `${config.projectName}-batch-${config.environment}`,
      removalPolicy: config.environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.MUTABLE,
      lifecycleRules: [
        {
          description: 'Keep only last 10 images',
          maxImageCount: 10,
          rulePriority: 1,
        },
      ],
    });

    // Outputs
    new cdk.CfnOutput(this, 'ApiRepositoryUri', {
      value: this.apiRepository.repositoryUri,
      description: 'ECR repository URI for API container',
      exportName: `${config.projectName}-ApiRepository-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'ApiRepositoryArn', {
      value: this.apiRepository.repositoryArn,
      description: 'ECR repository ARN for API container',
      exportName: `${config.projectName}-ApiRepositoryArn-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'BatchRepositoryUri', {
      value: this.batchRepository.repositoryUri,
      description: 'ECR repository URI for Batch container',
      exportName: `${config.projectName}-BatchRepository-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'BatchRepositoryArn', {
      value: this.batchRepository.repositoryArn,
      description: 'ECR repository ARN for Batch container',
      exportName: `${config.projectName}-BatchRepositoryArn-${config.environment}`,
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'EcrStack');
    cdk.Tags.of(this).add('Environment', config.environment);
  }
}
