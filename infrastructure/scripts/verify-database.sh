#!/bin/bash

# Verify DynamoDB Database Configuration
# This script verifies that the DynamoDB table is properly configured with:
# - Primary key (task_id, created_at)
# - Global Secondary Indexes (StatusIndex, BatchJobIndex, UserIndex)
# - TTL configuration
# - Basic read/write operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
TABLE_NAME="ProcessingTasks-${ENVIRONMENT}"
REGION=${AWS_REGION:-us-east-1}

echo "=========================================="
echo "DynamoDB Database Verification"
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Table Name: ${TABLE_NAME}"
echo "Region: ${REGION}"
echo ""

# Function to print success message
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error message
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print info message
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    exit 1
fi

# Check if table exists
echo "1. Checking if table exists..."
if aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}" &> /dev/null; then
    print_success "Table '${TABLE_NAME}' exists"
else
    print_error "Table '${TABLE_NAME}' does not exist"
    echo ""
    print_info "Please deploy the database stack first:"
    echo "  cd infrastructure"
    echo "  npm run cdk deploy SatelliteGis-Database-${ENVIRONMENT}"
    exit 1
fi

# Get table description
TABLE_DESC=$(aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}")

echo ""
echo "2. Verifying primary key configuration..."

# Check partition key
PARTITION_KEY=$(echo "${TABLE_DESC}" | jq -r '.Table.KeySchema[] | select(.KeyType=="HASH") | .AttributeName')
if [ "${PARTITION_KEY}" == "task_id" ]; then
    print_success "Partition key is 'task_id'"
else
    print_error "Partition key is '${PARTITION_KEY}', expected 'task_id'"
fi

# Check sort key
SORT_KEY=$(echo "${TABLE_DESC}" | jq -r '.Table.KeySchema[] | select(.KeyType=="RANGE") | .AttributeName')
if [ "${SORT_KEY}" == "created_at" ]; then
    print_success "Sort key is 'created_at'"
else
    print_error "Sort key is '${SORT_KEY}', expected 'created_at'"
fi

echo ""
echo "3. Verifying Global Secondary Indexes (GSI)..."

# Check StatusIndex
STATUS_INDEX=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="StatusIndex") | .IndexName')
if [ "${STATUS_INDEX}" == "StatusIndex" ]; then
    print_success "StatusIndex exists"
    STATUS_INDEX_PK=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="StatusIndex") | .KeySchema[] | select(.KeyType=="HASH") | .AttributeName')
    STATUS_INDEX_SK=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="StatusIndex") | .KeySchema[] | select(.KeyType=="RANGE") | .AttributeName')
    if [ "${STATUS_INDEX_PK}" == "status" ] && [ "${STATUS_INDEX_SK}" == "created_at" ]; then
        print_success "  - Keys: status (PK), created_at (SK)"
    else
        print_error "  - Keys: ${STATUS_INDEX_PK} (PK), ${STATUS_INDEX_SK} (SK) - Expected: status, created_at"
    fi
else
    print_error "StatusIndex does not exist"
fi

# Check BatchJobIndex
BATCH_INDEX=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="BatchJobIndex") | .IndexName')
if [ "${BATCH_INDEX}" == "BatchJobIndex" ]; then
    print_success "BatchJobIndex exists"
    BATCH_INDEX_PK=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="BatchJobIndex") | .KeySchema[] | select(.KeyType=="HASH") | .AttributeName')
    if [ "${BATCH_INDEX_PK}" == "batch_job_id" ]; then
        print_success "  - Key: batch_job_id (PK)"
    else
        print_error "  - Key: ${BATCH_INDEX_PK} (PK) - Expected: batch_job_id"
    fi
else
    print_error "BatchJobIndex does not exist"
fi

# Check UserIndex
USER_INDEX=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="UserIndex") | .IndexName')
if [ "${USER_INDEX}" == "UserIndex" ]; then
    print_success "UserIndex exists"
    USER_INDEX_PK=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="UserIndex") | .KeySchema[] | select(.KeyType=="HASH") | .AttributeName')
    USER_INDEX_SK=$(echo "${TABLE_DESC}" | jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="UserIndex") | .KeySchema[] | select(.KeyType=="RANGE") | .AttributeName')
    if [ "${USER_INDEX_PK}" == "user_id" ] && [ "${USER_INDEX_SK}" == "created_at" ]; then
        print_success "  - Keys: user_id (PK), created_at (SK)"
    else
        print_error "  - Keys: ${USER_INDEX_PK} (PK), ${USER_INDEX_SK} (SK) - Expected: user_id, created_at"
    fi
else
    print_error "UserIndex does not exist"
fi

echo ""
echo "4. Verifying TTL configuration..."

# Check TTL
TTL_DESC=$(aws dynamodb describe-time-to-live --table-name "${TABLE_NAME}" --region "${REGION}")
TTL_STATUS=$(echo "${TTL_DESC}" | jq -r '.TimeToLiveDescription.TimeToLiveStatus')
TTL_ATTRIBUTE=$(echo "${TTL_DESC}" | jq -r '.TimeToLiveDescription.AttributeName')

if [ "${TTL_STATUS}" == "ENABLED" ]; then
    print_success "TTL is enabled"
    if [ "${TTL_ATTRIBUTE}" == "expiresAt" ]; then
        print_success "  - TTL attribute: expiresAt"
    else
        print_error "  - TTL attribute: ${TTL_ATTRIBUTE} - Expected: expiresAt"
    fi
elif [ "${TTL_STATUS}" == "ENABLING" ]; then
    print_info "TTL is being enabled (status: ENABLING)"
    print_info "  - TTL attribute: ${TTL_ATTRIBUTE}"
else
    print_error "TTL is not enabled (status: ${TTL_STATUS})"
fi

echo ""
echo "5. Testing basic read/write operations..."

# Generate test data
TEST_TASK_ID="test-task-$(date +%s)"
TEST_CREATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TEST_EXPIRES_AT=$(date -u -d "+30 days" +%s 2>/dev/null || date -u -v+30d +%s)

# Write test item
print_info "Writing test item..."
aws dynamodb put-item \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --item "{
        \"task_id\": {\"S\": \"${TEST_TASK_ID}\"},
        \"created_at\": {\"S\": \"${TEST_CREATED_AT}\"},
        \"status\": {\"S\": \"queued\"},
        \"task_type\": {\"S\": \"test\"},
        \"user_id\": {\"S\": \"test-user\"},
        \"batch_job_id\": {\"S\": \"test-batch-job-123\"},
        \"expiresAt\": {\"N\": \"${TEST_EXPIRES_AT}\"},
        \"parameters\": {\"M\": {}}
    }" &> /dev/null

if [ $? -eq 0 ]; then
    print_success "Successfully wrote test item"
else
    print_error "Failed to write test item"
    exit 1
fi

# Read test item
print_info "Reading test item..."
READ_RESULT=$(aws dynamodb get-item \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --key "{
        \"task_id\": {\"S\": \"${TEST_TASK_ID}\"},
        \"created_at\": {\"S\": \"${TEST_CREATED_AT}\"}
    }")

if [ $? -eq 0 ]; then
    RETRIEVED_TASK_ID=$(echo "${READ_RESULT}" | jq -r '.Item.task_id.S')
    if [ "${RETRIEVED_TASK_ID}" == "${TEST_TASK_ID}" ]; then
        print_success "Successfully read test item"
    else
        print_error "Read item does not match written item"
    fi
else
    print_error "Failed to read test item"
fi

# Query by status using GSI
print_info "Querying by status using StatusIndex..."
QUERY_RESULT=$(aws dynamodb query \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --index-name "StatusIndex" \
    --key-condition-expression "status = :status" \
    --expression-attribute-values '{":status": {"S": "queued"}}' \
    --limit 1)

if [ $? -eq 0 ]; then
    QUERY_COUNT=$(echo "${QUERY_RESULT}" | jq -r '.Count')
    if [ "${QUERY_COUNT}" -gt 0 ]; then
        print_success "Successfully queried by status (found ${QUERY_COUNT} items)"
    else
        print_error "Query returned 0 items"
    fi
else
    print_error "Failed to query by status"
fi

# Query by batch_job_id using GSI
print_info "Querying by batch_job_id using BatchJobIndex..."
BATCH_QUERY_RESULT=$(aws dynamodb query \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --index-name "BatchJobIndex" \
    --key-condition-expression "batch_job_id = :batch_job_id" \
    --expression-attribute-values '{":batch_job_id": {"S": "test-batch-job-123"}}')

if [ $? -eq 0 ]; then
    BATCH_QUERY_COUNT=$(echo "${BATCH_QUERY_RESULT}" | jq -r '.Count')
    if [ "${BATCH_QUERY_COUNT}" -gt 0 ]; then
        print_success "Successfully queried by batch_job_id (found ${BATCH_QUERY_COUNT} items)"
    else
        print_error "Query returned 0 items"
    fi
else
    print_error "Failed to query by batch_job_id"
fi

# Update test item
print_info "Updating test item..."
aws dynamodb update-item \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --key "{
        \"task_id\": {\"S\": \"${TEST_TASK_ID}\"},
        \"created_at\": {\"S\": \"${TEST_CREATED_AT}\"}
    }" \
    --update-expression "SET #status = :status, updated_at = :updated_at" \
    --expression-attribute-names '{"#status": "status"}' \
    --expression-attribute-values "{
        \":status\": {\"S\": \"completed\"},
        \":updated_at\": {\"S\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}
    }" &> /dev/null

if [ $? -eq 0 ]; then
    print_success "Successfully updated test item"
else
    print_error "Failed to update test item"
fi

# Delete test item
print_info "Deleting test item..."
aws dynamodb delete-item \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --key "{
        \"task_id\": {\"S\": \"${TEST_TASK_ID}\"},
        \"created_at\": {\"S\": \"${TEST_CREATED_AT}\"}
    }" &> /dev/null

if [ $? -eq 0 ]; then
    print_success "Successfully deleted test item"
else
    print_error "Failed to delete test item"
fi

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
print_success "Database verification completed successfully!"
echo ""
echo "Table Details:"
echo "  - Name: ${TABLE_NAME}"
echo "  - Region: ${REGION}"
echo "  - Primary Key: task_id (PK), created_at (SK)"
echo "  - GSI: StatusIndex, BatchJobIndex, UserIndex"
echo "  - TTL: ${TTL_STATUS} (attribute: ${TTL_ATTRIBUTE})"
echo ""
