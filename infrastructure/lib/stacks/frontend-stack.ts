import * as cdk from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface FrontendStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiUrl: string;
  apiKeyId: string;
}

export class FrontendStack extends cdk.Stack {
  public readonly amplifyApp: amplify.CfnApp;
  public readonly amplifyBranch: amplify.CfnBranch;
  public readonly websiteUrl: string;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const { config, apiUrl, apiKeyId } = props;

    // Create IAM role for Amplify
    const amplifyRole = new iam.Role(this, 'AmplifyRole', {
      assumedBy: new iam.ServicePrincipal('amplify.amazonaws.com'),
      description: 'Role for Amplify to build and deploy frontend',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess-Amplify'),
      ],
    });

    // Create Amplify App
    this.amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: `satellite-gis-${config.environment}`,
      description: `Satellite GIS Platform Frontend (${config.environment})`,
      
      // Repository configuration - connect to GitHub
      repository: config.frontend.repositoryUrl,
      accessToken: config.frontend.githubToken,
      
      // IAM service role
      iamServiceRole: amplifyRole.roleArn,
      
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
          name: 'REACT_APP_API_KEY_ID',
          value: apiKeyId,
        },
        {
          name: 'REACT_APP_ENVIRONMENT',
          value: config.environment,
        },
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

    // Create branch (main/master or environment-specific)
    const branchName = config.frontend.branchName || config.environment;
    this.amplifyBranch = new amplify.CfnBranch(this, 'AmplifyBranch', {
      appId: this.amplifyApp.attrAppId,
      branchName: branchName,
      description: `${config.environment} environment branch`,
      enableAutoBuild: true,
      enablePullRequestPreview: config.environment !== 'prod',
      stage: config.environment === 'prod' ? 'PRODUCTION' : 'DEVELOPMENT',
      
      // Environment variables specific to this branch
      environmentVariables: [
        {
          name: 'REACT_APP_API_URL',
          value: apiUrl,
        },
        {
          name: 'REACT_APP_API_KEY_ID',
          value: apiKeyId,
        },
      ],
    });

    // Set the website URL
    this.websiteUrl = `https://${branchName}.${this.amplifyApp.attrDefaultDomain}`;

    // If custom domain is configured
    if (config.frontend.domainName) {
      const domain = new amplify.CfnDomain(this, 'AmplifyDomain', {
        appId: this.amplifyApp.attrAppId,
        domainName: config.frontend.domainName,
        subDomainSettings: [
          {
            branchName: branchName,
            prefix: config.environment === 'prod' ? '' : config.environment,
          },
        ],
        enableAutoSubDomain: false,
      });

      this.websiteUrl = config.environment === 'prod'
        ? `https://${config.frontend.domainName}`
        : `https://${config.environment}.${config.frontend.domainName}`;
    }

    // Outputs
    new cdk.CfnOutput(this, 'AmplifyAppId', {
      value: this.amplifyApp.attrAppId,
      description: 'Amplify App ID',
      exportName: `SatelliteGis-AmplifyAppId-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'AmplifyAppName', {
      value: this.amplifyApp.name!,
      description: 'Amplify App Name',
      exportName: `SatelliteGis-AmplifyAppName-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'AmplifyDefaultDomain', {
      value: this.amplifyApp.attrDefaultDomain,
      description: 'Amplify default domain',
      exportName: `SatelliteGis-AmplifyDomain-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'WebsiteUrl', {
      value: this.websiteUrl,
      description: 'Frontend website URL',
      exportName: `SatelliteGis-WebsiteUrl-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'FrontendConfig', {
      value: JSON.stringify({
        apiUrl: apiUrl,
        environment: config.environment,
      }),
      description: 'Frontend configuration JSON',
      exportName: `SatelliteGis-FrontendConfig-${config.environment}`,
    });

    // Output custom domain (if configured)
    if (config.frontend.domainName) {
      new cdk.CfnOutput(this, 'CustomDomain', {
        value: config.frontend.domainName,
        description: 'Custom domain name',
        exportName: `SatelliteGis-CustomDomain-${config.environment}`,
      });
    }

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
