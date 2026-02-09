import * as cdk from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as cr from 'aws-cdk-lib/custom-resources';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface FrontendStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiUrl: string;
  apiKeyId: string;  // API Key ID (will fetch value using Custom Resource)
  userPoolId?: string;
  userPoolClientId?: string;
  identityPoolId?: string;
}

export class FrontendStack extends cdk.Stack {
  public readonly amplifyApp: amplify.CfnApp;
  public readonly amplifyBranch: amplify.CfnBranch;
  public readonly websiteUrl: string;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const { config, apiUrl, apiKeyId, userPoolId, userPoolClientId, identityPoolId } = props;

    // Get API Key value using Custom Resource
    const getApiKeyValue = new cr.AwsCustomResource(this, 'GetApiKeyValue', {
      onCreate: {
        service: 'APIGateway',
        action: 'getApiKey',
        parameters: {
          apiKey: apiKeyId,
          includeValue: true,
        },
        physicalResourceId: cr.PhysicalResourceId.of(apiKeyId),
      },
      onUpdate: {
        service: 'APIGateway',
        action: 'getApiKey',
        parameters: {
          apiKey: apiKeyId,
          includeValue: true,
        },
        physicalResourceId: cr.PhysicalResourceId.of(apiKeyId),
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['apigateway:GET'],
          resources: ['*'],  // API Gateway API Keys don't support resource-level permissions
        }),
      ]),
    });

    const apiKey = getApiKeyValue.getResponseField('value');

    // Create IAM role for Amplify
    const amplifyRole = new iam.Role(this, 'AmplifyRole', {
      assumedBy: new iam.ServicePrincipal('amplify.amazonaws.com'),
      description: 'Role for Amplify to build and deploy frontend',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess-Amplify'),
      ],
    });

    // Create Amplify App without repository connection
    // Repository will be connected manually via AWS Console using OAuth
    this.amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: `satellite-gis-${config.environment}`,
      description: `Satellite GIS Platform Frontend (${config.environment}) - Connect repository via AWS Console`,
      
      // No repository configuration - will be connected manually via Console
      // This allows using OAuth instead of Personal Access Token
      
      // IAM service role
      iamServiceRole: amplifyRole.roleArn,
      
      // Platform: WEB for React apps
      platform: 'WEB',
      
      // Build settings
      buildSpec: this.getBuildSpec(apiUrl, config.environment),
      
      // Pre-configure environment variables (will be used when repository is connected)
      environmentVariables: [
        {
          name: 'REACT_APP_API_URL',
          value: apiUrl,
        },
        {
          name: 'REACT_APP_API_KEY',
          value: apiKey,
        },
        {
          name: 'REACT_APP_ENVIRONMENT',
          value: config.environment,
        },
        ...(userPoolId ? [{
          name: 'REACT_APP_USER_POOL_ID',
          value: userPoolId,
        }] : []),
        ...(userPoolClientId ? [{
          name: 'REACT_APP_USER_POOL_CLIENT_ID',
          value: userPoolClientId,
        }] : []),
        ...(identityPoolId ? [{
          name: 'REACT_APP_IDENTITY_POOL_ID',
          value: identityPoolId,
        }] : []),
        {
          name: '_LIVE_UPDATES',
          value: JSON.stringify([
            {
              pkg: 'node',
              type: 'nvm',
              version: '18',
            },
          ]),
        },
      ],
      
      // Platform: WEB for React apps
      platform: 'WEB',
      
      // Build settings
      buildSpec: this.getBuildSpec(apiUrl, config.environment),
      
      // Environment variables
      environmentVariables: [
        {
          name: 'REACT_APP_API_URL',
          value: apiUrl,
        },
        {
          name: 'REACT_APP_API_KEY',
          value: apiKey,
        },
        {
          name: 'REACT_APP_ENVIRONMENT',
          value: config.environment,
        },
        ...(userPoolId ? [{
          name: 'REACT_APP_USER_POOL_ID',
          value: userPoolId,
        }] : []),
        ...(userPoolClientId ? [{
          name: 'REACT_APP_USER_POOL_CLIENT_ID',
          value: userPoolClientId,
        }] : []),
        ...(identityPoolId ? [{
          name: 'REACT_APP_IDENTITY_POOL_ID',
          value: identityPoolId,
        }] : []),
        {
          name: '_LIVE_UPDATES',
          value: JSON.stringify([
            {
              pkg: 'node',
              type: 'nvm',
              version: '18',
            },
          ]),
        },
      ],
      
      // Custom rules for SPA routing
      customRules: [
        {
          source: '</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>',
          target: '/index.html',
          status: '200',
        },
      ],
      
      // Custom headers for security
      customHeaders: `
customHeaders:
  - pattern: '**/*'
    headers:
      - key: 'Strict-Transport-Security'
        value: 'max-age=31536000; includeSubDomains'
      - key: 'X-Frame-Options'
        value: 'SAMEORIGIN'
      - key: 'X-Content-Type-Options'
        value: 'nosniff'
      - key: 'X-XSS-Protection'
        value: '1; mode=block'
      - key: 'Referrer-Policy'
        value: 'strict-origin-when-cross-origin'
      `,
    });

    // Note: Branch will be created after connecting repository via AWS Console
    // The following outputs will help with manual setup
    
    // Set the website URL (will be available after connecting repository)
    this.websiteUrl = `https://${this.amplifyApp.attrDefaultDomain}`;

    // Outputs
    new cdk.CfnOutput(this, 'AmplifyAppId', {
      value: this.amplifyApp.attrAppId,
      description: 'Amplify App ID - Use this to connect repository in AWS Console',
      exportName: `SatelliteGis-AmplifyAppId-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'AmplifyAppName', {
      value: this.amplifyApp.name!,
      description: 'Amplify App Name',
      exportName: `SatelliteGis-AmplifyAppName-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'AmplifyConsoleUrl', {
      value: `https://console.aws.amazon.com/amplify/home?region=${this.region}#/${this.amplifyApp.attrAppId}`,
      description: 'AWS Amplify Console URL - Click to connect repository',
    });

    new cdk.CfnOutput(this, 'RepositoryUrl', {
      value: config.frontend.repositoryUrl || 'https://github.com/nwcd-solutions/agriculture-remote-sense',
      description: 'GitHub Repository URL to connect',
    });

    new cdk.CfnOutput(this, 'BranchName', {
      value: config.frontend.branchName || 'main',
      description: 'Git branch to deploy',
    });

    new cdk.CfnOutput(this, 'SetupInstructions', {
      value: 'After deployment, go to Amplify Console and click "Connect branch" to link your GitHub repository using OAuth',
      description: 'Next Steps',
    });

    new cdk.CfnOutput(this, 'EnvironmentVariables', {
      value: JSON.stringify({
        REACT_APP_API_URL: apiUrl,
        REACT_APP_API_KEY: '<will-be-set-in-console>',
        REACT_APP_ENVIRONMENT: config.environment,
        REACT_APP_USER_POOL_ID: userPoolId || '',
        REACT_APP_USER_POOL_CLIENT_ID: userPoolClientId || '',
        REACT_APP_IDENTITY_POOL_ID: identityPoolId || '',
      }, null, 2),
      description: 'Environment variables to configure in Amplify Console',
    });

    // Add tags
    cdk.Tags.of(this).add('Stack', 'Frontend');
    cdk.Tags.of(this).add('Platform', 'Amplify');
    Object.entries(config.tags).forEach(([key, value]) => {
      cdk.Tags.of(this).add(key, value);
    });
  }

  /**
   * Generate Amplify build spec for React app
   */
  private getBuildSpec(apiUrl: string, environment: string): string {
    return `
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - echo "REACT_APP_API_URL=${apiUrl}" >> .env.production
        - echo "REACT_APP_API_KEY=\${REACT_APP_API_KEY}" >> .env.production
        - echo "REACT_APP_ENVIRONMENT=${environment}" >> .env.production
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
`;
  }
}
