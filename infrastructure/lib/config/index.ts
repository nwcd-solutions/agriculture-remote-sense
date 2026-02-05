import { EnvironmentConfig } from './types';
import { devConfig } from './dev';
import { stagingConfig } from './staging';
import { prodConfig } from './prod';

export { EnvironmentConfig } from './types';

export function getConfig(environment?: string): EnvironmentConfig {
  const env = environment || process.env.ENVIRONMENT || 'dev';
  
  switch (env) {
    case 'dev':
      return devConfig;
    case 'staging':
      return stagingConfig;
    case 'prod':
      return prodConfig;
    default:
      console.warn(`Unknown environment: ${env}, defaulting to dev`);
      return devConfig;
  }
}
