import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface AuthStackProps extends cdk.StackProps {
  environment: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly identityPool: cognito.CfnIdentityPool;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // Pre-signup Lambda trigger for admin approval
    const preSignupLambda = new lambda.Function(this, 'PreSignupFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json

def handler(event, context):
    """
    Pre-signup trigger that auto-confirms user but keeps them disabled
    Admin must manually enable the user in Cognito console
    """
    # Auto-confirm the user
    event['response']['autoConfirmUser'] = True
    event['response']['autoVerifyEmail'] = True
    
    # Return the event
    return event
      `),
      description: 'Pre-signup trigger for user registration',
    });

    // Post-confirmation Lambda trigger to send admin notification
    const postConfirmationLambda = new lambda.Function(this, 'PostConfirmationFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import os

def handler(event, context):
    """
    Post-confirmation trigger to disable user and notify admin
    """
    cognito = boto3.client('cognito-idp')
    user_pool_id = event['userPoolId']
    username = event['userName']
    
    try:
        # Disable the user immediately after signup
        cognito.admin_disable_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        
        print(f"User {username} has been disabled pending admin approval")
        
        # TODO: Send notification to admin (SNS, SES, etc.)
        # For now, just log it
        
    except Exception as e:
        print(f"Error disabling user: {str(e)}")
    
    return event
      `),
      description: 'Post-confirmation trigger to disable user pending approval',
    });

    // Grant permissions to the post-confirmation Lambda
    postConfirmationLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['cognito-idp:AdminDisableUser'],
        resources: ['*'],
      })
    );

    // Create User Pool
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `satellite-gis-users-${environment}`,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
        username: true,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
        fullname: {
          required: true,
          mutable: true,
        },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lambdaTriggers: {
        preSignUp: preSignupLambda,
        postConfirmation: postConfirmationLambda,
      },
    });

    // Create User Pool Client
    this.userPoolClient = this.userPool.addClient('WebClient', {
      userPoolClientName: `satellite-gis-web-client-${environment}`,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      preventUserExistenceErrors: true,
    });

    // Create Identity Pool
    this.identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      identityPoolName: `satellite_gis_identity_${environment}`,
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          clientId: this.userPoolClient.userPoolClientId,
          providerName: this.userPool.userPoolProviderName,
        },
      ],
    });

    // Create IAM roles for authenticated users
    const authenticatedRole = new iam.Role(this, 'AuthenticatedRole', {
      assumedBy: new iam.FederatedPrincipal(
        'cognito-identity.amazonaws.com',
        {
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': this.identityPool.ref,
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'authenticated',
          },
        },
        'sts:AssumeRoleWithWebIdentity'
      ),
    });

    // Attach role to identity pool
    new cognito.CfnIdentityPoolRoleAttachment(this, 'IdentityPoolRoleAttachment', {
      identityPoolId: this.identityPool.ref,
      roles: {
        authenticated: authenticatedRole.roleArn,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${environment}-UserPoolId`,
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `${environment}-UserPoolClientId`,
    });

    new cdk.CfnOutput(this, 'IdentityPoolId', {
      value: this.identityPool.ref,
      description: 'Cognito Identity Pool ID',
      exportName: `${environment}-IdentityPoolId`,
    });

    new cdk.CfnOutput(this, 'UserPoolArn', {
      value: this.userPool.userPoolArn,
      description: 'Cognito User Pool ARN',
    });
  }
}
