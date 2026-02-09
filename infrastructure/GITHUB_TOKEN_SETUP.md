# GitHub Token Setup for AWS Amplify

## Why is a GitHub Token Required?

AWS Amplify requires a GitHub Personal Access Token (PAT) to:
1. Set up webhooks for automatic deployments
2. Access repository metadata
3. Clone the repository for builds

**Note**: Even for public repositories, Amplify needs a token to set up webhooks and automation.

## Creating a GitHub Personal Access Token

### Step 1: Go to GitHub Settings

1. Log in to GitHub
2. Click your profile picture → **Settings**
3. Scroll down and click **Developer settings** (left sidebar)
4. Click **Personal access tokens** → **Tokens (classic)**

### Step 2: Generate New Token

1. Click **Generate new token** → **Generate new token (classic)**
2. Give it a descriptive name: `AWS Amplify - Agriculture Remote Sense`
3. Set expiration: Choose based on your needs (e.g., 90 days, 1 year, or no expiration)

### Step 3: Select Scopes

For a **public repository**, you only need:
- ✅ `public_repo` - Access public repositories

For a **private repository**, you would need:
- ✅ `repo` - Full control of private repositories

### Step 4: Generate and Copy Token

1. Click **Generate token** at the bottom
2. **IMPORTANT**: Copy the token immediately - you won't be able to see it again!
3. Store it securely (e.g., in a password manager)

## Configuring the Token

### Option 1: Environment Variable (Recommended)

Set the token as an environment variable before deployment:

```bash
# On Linux/Mac
export GITHUB_TOKEN=ghp_your_token_here

# On Windows PowerShell
$env:GITHUB_TOKEN="ghp_your_token_here"

# On Windows CMD
set GITHUB_TOKEN=ghp_your_token_here
```

Then update `infrastructure/lib/config/dev.ts`:

```typescript
frontend: {
  // ...
  githubToken: process.env.GITHUB_TOKEN,
}
```

### Option 2: AWS Secrets Manager (Production)

For production environments, store the token in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name github-token \
  --secret-string "ghp_your_token_here" \
  --region us-east-2

# Retrieve in CDK code
const secret = secretsmanager.Secret.fromSecretNameV2(this, 'GitHubToken', 'github-token');
```

### Option 3: Direct Configuration (Not Recommended)

**WARNING**: Never commit tokens to Git!

Add to `infrastructure/lib/config/dev.ts`:

```typescript
frontend: {
  // ...
  githubToken: 'ghp_your_token_here', // NEVER commit this!
}
```

Make sure this file is in `.gitignore` or use a separate config file.

## Deployment

After configuring the token:

```bash
cd infrastructure
npx cdk deploy SatelliteGis-Frontend-dev --require-approval never --context environment=dev
```

## Security Best Practices

1. **Never commit tokens to Git**
   - Add config files with tokens to `.gitignore`
   - Use environment variables or AWS Secrets Manager

2. **Use minimal permissions**
   - For public repos: Only `public_repo` scope
   - For private repos: Only `repo` scope

3. **Rotate tokens regularly**
   - Set expiration dates
   - Update tokens before they expire

4. **Revoke unused tokens**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Revoke tokens you no longer need

## Troubleshooting

### Error: "Invalid request provided: You should at least provide one valid token"

**Cause**: No GitHub token provided or token is invalid.

**Solution**:
1. Verify token is set: `echo $GITHUB_TOKEN` (Linux/Mac) or `echo %GITHUB_TOKEN%` (Windows)
2. Verify token has correct permissions (public_repo for public repos)
3. Verify token hasn't expired
4. Generate a new token if needed

### Error: "Bad credentials"

**Cause**: Token is invalid or has been revoked.

**Solution**:
1. Generate a new token
2. Update the configuration
3. Redeploy

### Error: "Resource not accessible by integration"

**Cause**: Token doesn't have required permissions.

**Solution**:
1. Regenerate token with `public_repo` scope (for public repos)
2. Update configuration
3. Redeploy

## Alternative: Manual Amplify Connection

If you prefer not to use a token in CDK, you can:

1. Deploy the stack without the Amplify app
2. Manually connect the repository in AWS Amplify Console:
   - Go to AWS Amplify Console
   - Click "New app" → "Host web app"
   - Select "GitHub" and authorize via OAuth
   - Select your repository and branch
   - Configure build settings
   - Deploy

This approach uses OAuth instead of a PAT, but requires manual setup.

## References

- [GitHub Personal Access Tokens Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [AWS Amplify GitHub Integration](https://docs.aws.amazon.com/amplify/latest/userguide/setting-up-GitHub-access.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
