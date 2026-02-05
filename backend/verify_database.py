#!/usr/bin/env python3
"""
Standalone Database Verification Script

This script verifies that the DynamoDB table is properly configured.
Can be run without pytest for quick verification.

Usage:
    python verify_database.py [environment]
    
Example:
    python verify_database.py dev
"""

import os
import sys
import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError


# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_info(message):
    print(f"{Colors.YELLOW}ℹ {message}{Colors.NC}")


def verify_database(environment="dev", region="us-east-1"):
    """Verify DynamoDB database configuration"""
    
    table_name = f"ProcessingTasks-{environment}"
    
    print("=" * 60)
    print("DynamoDB Database Verification")
    print("=" * 60)
    print(f"Environment: {environment}")
    print(f"Table Name: {table_name}")
    print(f"Region: {region}")
    print()
    
    # Create clients
    dynamodb_client = boto3.client("dynamodb", region_name=region)
    dynamodb_resource = boto3.resource("dynamodb", region_name=region)
    table = dynamodb_resource.Table(table_name)
    
    verification_passed = True
    
    # 1. Check if table exists
    print("1. Checking if table exists...")
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        if response["Table"]["TableStatus"] == "ACTIVE":
            print_success(f"Table '{table_name}' exists and is ACTIVE")
        else:
            print_error(f"Table status is {response['Table']['TableStatus']}")
            verification_passed = False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print_error(f"Table '{table_name}' does not exist")
            print_info("Please deploy the database stack first:")
            print(f"  cd infrastructure")
            print(f"  npm run cdk deploy SatelliteGis-Database-{environment}")
            return False
        else:
            raise
    
    # 2. Verify primary key configuration
    print("\n2. Verifying primary key configuration...")
    key_schema = response["Table"]["KeySchema"]
    
    partition_key = next((k for k in key_schema if k["KeyType"] == "HASH"), None)
    if partition_key and partition_key["AttributeName"] == "task_id":
        print_success("Partition key is 'task_id'")
    else:
        print_error(f"Partition key is incorrect: {partition_key}")
        verification_passed = False
    
    sort_key = next((k for k in key_schema if k["KeyType"] == "RANGE"), None)
    if sort_key and sort_key["AttributeName"] == "created_at":
        print_success("Sort key is 'created_at'")
    else:
        print_error(f"Sort key is incorrect: {sort_key}")
        verification_passed = False
    
    # 3. Verify Global Secondary Indexes
    print("\n3. Verifying Global Secondary Indexes (GSI)...")
    gsi_list = response["Table"].get("GlobalSecondaryIndexes", [])
    
    # Check StatusIndex
    status_index = next((idx for idx in gsi_list if idx["IndexName"] == "StatusIndex"), None)
    if status_index:
        print_success("StatusIndex exists")
        key_schema = status_index["KeySchema"]
        pk = next((k for k in key_schema if k["KeyType"] == "HASH"), None)
        sk = next((k for k in key_schema if k["KeyType"] == "RANGE"), None)
        if pk["AttributeName"] == "status" and sk["AttributeName"] == "created_at":
            print_success("  - Keys: status (PK), created_at (SK)")
        else:
            print_error(f"  - Keys are incorrect")
            verification_passed = False
    else:
        print_error("StatusIndex does not exist")
        verification_passed = False
    
    # Check BatchJobIndex
    batch_index = next((idx for idx in gsi_list if idx["IndexName"] == "BatchJobIndex"), None)
    if batch_index:
        print_success("BatchJobIndex exists")
        key_schema = batch_index["KeySchema"]
        pk = next((k for k in key_schema if k["KeyType"] == "HASH"), None)
        if pk["AttributeName"] == "batch_job_id":
            print_success("  - Key: batch_job_id (PK)")
        else:
            print_error(f"  - Key is incorrect")
            verification_passed = False
    else:
        print_error("BatchJobIndex does not exist")
        verification_passed = False
    
    # Check UserIndex
    user_index = next((idx for idx in gsi_list if idx["IndexName"] == "UserIndex"), None)
    if user_index:
        print_success("UserIndex exists")
        key_schema = user_index["KeySchema"]
        pk = next((k for k in key_schema if k["KeyType"] == "HASH"), None)
        sk = next((k for k in key_schema if k["KeyType"] == "RANGE"), None)
        if pk["AttributeName"] == "user_id" and sk["AttributeName"] == "created_at":
            print_success("  - Keys: user_id (PK), created_at (SK)")
        else:
            print_error(f"  - Keys are incorrect")
            verification_passed = False
    else:
        print_error("UserIndex does not exist")
        verification_passed = False
    
    # 4. Verify TTL configuration
    print("\n4. Verifying TTL configuration...")
    try:
        ttl_response = dynamodb_client.describe_time_to_live(TableName=table_name)
        ttl_desc = ttl_response["TimeToLiveDescription"]
        ttl_status = ttl_desc["TimeToLiveStatus"]
        
        if ttl_status == "ENABLED":
            ttl_attribute = ttl_desc["AttributeName"]
            print_success("TTL is enabled")
            if ttl_attribute == "expiresAt":
                print_success(f"  - TTL attribute: {ttl_attribute}")
            else:
                print_error(f"  - TTL attribute is '{ttl_attribute}', expected 'expiresAt'")
                verification_passed = False
        elif ttl_status == "ENABLING":
            print_info("TTL is being enabled (status: ENABLING)")
        else:
            print_error(f"TTL is not enabled (status: {ttl_status})")
            verification_passed = False
    except ClientError as e:
        print_error(f"Failed to check TTL: {e}")
        verification_passed = False
    
    # 5. Test basic read/write operations
    print("\n5. Testing basic read/write operations...")
    
    test_task_id = f"test-task-{int(datetime.now(timezone.utc).timestamp())}"
    test_created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    test_expires_at = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    test_batch_job_id = f"test-batch-job-{int(datetime.now(timezone.utc).timestamp())}"
    
    # Write test item
    print_info("Writing test item...")
    try:
        table.put_item(
            Item={
                "task_id": test_task_id,
                "created_at": test_created_at,
                "status": "queued",
                "task_type": "test",
                "user_id": "test-user",
                "batch_job_id": test_batch_job_id,
                "expiresAt": test_expires_at,
                "parameters": {},
            }
        )
        print_success("Successfully wrote test item")
    except ClientError as e:
        print_error(f"Failed to write test item: {e}")
        verification_passed = False
        return verification_passed
    
    # Read test item
    print_info("Reading test item...")
    try:
        response = table.get_item(
            Key={
                "task_id": test_task_id,
                "created_at": test_created_at,
            }
        )
        if "Item" in response and response["Item"]["task_id"] == test_task_id:
            print_success("Successfully read test item")
        else:
            print_error("Failed to read test item correctly")
            verification_passed = False
    except ClientError as e:
        print_error(f"Failed to read test item: {e}")
        verification_passed = False
    
    # Query by status
    print_info("Querying by status using StatusIndex...")
    try:
        response = table.query(
            IndexName="StatusIndex",
            KeyConditionExpression="#status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "queued"},
            Limit=10,
        )
        if response["Count"] > 0:
            print_success(f"Successfully queried by status (found {response['Count']} items)")
        else:
            print_error("Query returned 0 items")
            verification_passed = False
    except ClientError as e:
        print_error(f"Failed to query by status: {e}")
        verification_passed = False
    
    # Query by batch_job_id
    print_info("Querying by batch_job_id using BatchJobIndex...")
    try:
        response = table.query(
            IndexName="BatchJobIndex",
            KeyConditionExpression="batch_job_id = :batch_job_id",
            ExpressionAttributeValues={":batch_job_id": test_batch_job_id},
        )
        if response["Count"] > 0:
            print_success(f"Successfully queried by batch_job_id (found {response['Count']} items)")
        else:
            print_error("Query returned 0 items")
            verification_passed = False
    except ClientError as e:
        print_error(f"Failed to query by batch_job_id: {e}")
        verification_passed = False
    
    # Update test item
    print_info("Updating test item...")
    try:
        table.update_item(
            Key={
                "task_id": test_task_id,
                "created_at": test_created_at,
            },
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "completed",
                ":updated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            },
        )
        print_success("Successfully updated test item")
    except ClientError as e:
        print_error(f"Failed to update test item: {e}")
        verification_passed = False
    
    # Delete test item (cleanup)
    print_info("Deleting test item...")
    try:
        table.delete_item(
            Key={
                "task_id": test_task_id,
                "created_at": test_created_at,
            }
        )
        print_success("Successfully deleted test item")
    except ClientError as e:
        print_error(f"Failed to delete test item: {e}")
        verification_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    if verification_passed:
        print_success("Database verification completed successfully!")
        print()
        print("Table Details:")
        print(f"  - Name: {table_name}")
        print(f"  - Region: {region}")
        print(f"  - Primary Key: task_id (PK), created_at (SK)")
        print(f"  - GSI: StatusIndex, BatchJobIndex, UserIndex")
        print(f"  - TTL: {ttl_status} (attribute: {ttl_desc.get('AttributeName', 'N/A')})")
        print()
        return True
    else:
        print_error("Database verification failed!")
        print_info("Please check the errors above and fix the configuration.")
        print()
        return False


if __name__ == "__main__":
    environment = sys.argv[1] if len(sys.argv) > 1 else "dev"
    region = os.getenv("AWS_REGION", "us-east-1")
    
    success = verify_database(environment, region)
    sys.exit(0 if success else 1)
