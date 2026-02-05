#!/bin/bash

# Verification script for CDK stacks
# This script verifies that all stacks can be synthesized correctly

set -e

echo "🔍 Verifying CDK Infrastructure Stacks..."
echo ""

# Change to infrastructure directory
cd "$(dirname "$0")/.."

# Build TypeScript
echo "📦 Building TypeScript..."
npm run build
echo "✅ TypeScript build successful"
echo ""

# Synthesize all stacks
echo "🔨 Synthesizing CloudFormation templates..."
npm run synth > /dev/null 2>&1
echo "✅ CloudFormation synthesis successful"
echo ""

# Check for generated templates
echo "📄 Checking generated templates..."
TEMPLATES=(
    "cdk.out/SatelliteGis-Network-dev.template.json"
    "cdk.out/SatelliteGis-Storage-dev.template.json"
    "cdk.out/SatelliteGis-Database-dev.template.json"
)

for template in "${TEMPLATES[@]}"; do
    if [ -f "$template" ]; then
        echo "  ✅ $(basename $template)"
    else
        echo "  ❌ $(basename $template) - NOT FOUND"
        exit 1
    fi
done
echo ""

# Verify Storage Stack configuration
echo "🗄️  Verifying Storage Stack..."
if grep -q "LifecycleConfiguration" cdk.out/SatelliteGis-Storage-dev.template.json; then
    echo "  ✅ Lifecycle rules configured"
else
    echo "  ❌ Lifecycle rules missing"
    exit 1
fi

if grep -q "CorsConfiguration" cdk.out/SatelliteGis-Storage-dev.template.json; then
    echo "  ✅ CORS configuration present"
else
    echo "  ❌ CORS configuration missing"
    exit 1
fi

if grep -q "BucketEncryption" cdk.out/SatelliteGis-Storage-dev.template.json; then
    echo "  ✅ Encryption enabled"
else
    echo "  ❌ Encryption not configured"
    exit 1
fi
echo ""

# Verify Database Stack configuration
echo "🗃️  Verifying Database Stack..."
if grep -q "GlobalSecondaryIndexes" cdk.out/SatelliteGis-Database-dev.template.json; then
    echo "  ✅ Global Secondary Indexes configured"
else
    echo "  ❌ GSI missing"
    exit 1
fi

if grep -q "TimeToLiveSpecification" cdk.out/SatelliteGis-Database-dev.template.json; then
    echo "  ✅ TTL configuration present"
else
    echo "  ❌ TTL not configured"
    exit 1
fi

if grep -q "StreamSpecification" cdk.out/SatelliteGis-Database-dev.template.json; then
    echo "  ✅ DynamoDB Streams enabled"
else
    echo "  ❌ Streams not enabled"
    exit 1
fi
echo ""

# Count resources
echo "📊 Resource Summary:"
for template in "${TEMPLATES[@]}"; do
    stack_name=$(basename $template .template.json)
    resource_count=$(jq '.Resources | length' "$template")
    echo "  $stack_name: $resource_count resources"
done
echo ""

echo "✨ All verifications passed!"
echo ""
echo "Next steps:"
echo "  1. Review the generated templates in cdk.out/"
echo "  2. Deploy to dev: npm run deploy:dev"
echo "  3. Verify resources in AWS Console"
