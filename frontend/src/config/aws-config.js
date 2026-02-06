// AWS Amplify Configuration
export const awsConfig = {
  Auth: {
    region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
    identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID,
    mandatorySignIn: true,
  },
  API: {
    endpoints: [
      {
        name: 'SatelliteGIS',
        endpoint: process.env.REACT_APP_API_URL,
        custom_header: async () => {
          return {
            'X-Api-Key': process.env.REACT_APP_API_KEY || '',
          };
        },
      },
    ],
  },
};
