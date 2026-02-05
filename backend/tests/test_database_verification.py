"""
Database Configuration Verification Tests

This test suite verifies that the DynamoDB table is properly configured with:
- Primary key (task_id, created_at)
- Global Secondary Indexes (StatusIndex, BatchJobIndex, UserIndex)
- TTL configuration
- Basic read/write operations

Requirements: 9.10, 10.4
"""

import os
import pytest
import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError


# Test configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
TABLE_NAME = f"ProcessingTasks-{ENVIRONMENT}"
REGION = os.getenv("AWS_REGION", "us-east-1")


@pytest.fixture(scope="module")
def dynamodb_client():
    """Create DynamoDB client"""
    return boto3.client("dynamodb", region_name=REGION)


@pytest.fixture(scope="module")
def dynamodb_resource():
    """Create DynamoDB resource"""
    return boto3.resource("dynamodb", region_name=REGION)


@pytest.fixture(scope="module")
def table(dynamodb_resource):
    """Get DynamoDB table"""
    return dynamodb_resource.Table(TABLE_NAME)


class TestDatabaseConfiguration:
    """Test suite for database configuration verification"""

    def test_table_exists(self, dynamodb_client):
        """Test 1: Verify that the DynamoDB table exists"""
        try:
            response = dynamodb_client.describe_table(TableName=TABLE_NAME)
            assert response["Table"]["TableName"] == TABLE_NAME
            assert response["Table"]["TableStatus"] == "ACTIVE"
            print(f"✓ Table '{TABLE_NAME}' exists and is ACTIVE")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                pytest.fail(
                    f"Table '{TABLE_NAME}' does not exist. "
                    f"Please deploy the database stack first."
                )
            else:
                raise

    def test_primary_key_configuration(self, dynamodb_client):
        """Test 2: Verify primary key configuration (partition key and sort key)"""
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        key_schema = response["Table"]["KeySchema"]
        
        # Check partition key
        partition_key = next(
            (k for k in key_schema if k["KeyType"] == "HASH"), None
        )
        assert partition_key is not None, "Partition key not found"
        assert partition_key["AttributeName"] == "task_id", (
            f"Partition key is '{partition_key['AttributeName']}', expected 'task_id'"
        )
        print("✓ Partition key is 'task_id'")
        
        # Check sort key
        sort_key = next(
            (k for k in key_schema if k["KeyType"] == "RANGE"), None
        )
        assert sort_key is not None, "Sort key not found"
        assert sort_key["AttributeName"] == "created_at", (
            f"Sort key is '{sort_key['AttributeName']}', expected 'created_at'"
        )
        print("✓ Sort key is 'created_at'")

    def test_attribute_definitions(self, dynamodb_client):
        """Test 3: Verify attribute definitions"""
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        attributes = {
            attr["AttributeName"]: attr["AttributeType"]
            for attr in response["Table"]["AttributeDefinitions"]
        }
        
        # Check required attributes
        required_attributes = {
            "task_id": "S",
            "created_at": "S",
            "status": "S",
            "batch_job_id": "S",
            "user_id": "S",
        }
        
        for attr_name, attr_type in required_attributes.items():
            assert attr_name in attributes, f"Attribute '{attr_name}' not defined"
            assert attributes[attr_name] == attr_type, (
                f"Attribute '{attr_name}' has type '{attributes[attr_name]}', "
                f"expected '{attr_type}'"
            )
        
        print(f"✓ All required attributes are defined: {list(required_attributes.keys())}")

    def test_status_index_configuration(self, dynamodb_client):
        """Test 4: Verify StatusIndex GSI configuration"""
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        gsi_list = response["Table"].get("GlobalSecondaryIndexes", [])
        
        status_index = next(
            (idx for idx in gsi_list if idx["IndexName"] == "StatusIndex"), None
        )
        assert status_index is not None, "StatusIndex does not exist"
        assert status_index["IndexStatus"] == "ACTIVE", (
            f"StatusIndex status is '{status_index['IndexStatus']}', expected 'ACTIVE'"
        )
        
        # Check keys
        key_schema = status_index["KeySchema"]
        partition_key = next(
            (k for k in key_schema if k["KeyType"] == "HASH"), None
        )
        sort_key = next(
            (k for k in key_schema if k["KeyType"] == "RANGE"), None
        )
        
        assert partition_key["AttributeName"] == "status"
        assert sort_key["AttributeName"] == "created_at"
        
        # Check projection
        assert status_index["Projection"]["ProjectionType"] == "ALL"
        
        print("✓ StatusIndex exists with correct configuration")
        print("  - Keys: status (PK), created_at (SK)")
        print("  - Projection: ALL")

    def test_batch_job_index_configuration(self, dynamodb_client):
        """Test 5: Verify BatchJobIndex GSI configuration"""
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        gsi_list = response["Table"].get("GlobalSecondaryIndexes", [])
        
        batch_index = next(
            (idx for idx in gsi_list if idx["IndexName"] == "BatchJobIndex"), None
        )
        assert batch_index is not None, "BatchJobIndex does not exist"
        assert batch_index["IndexStatus"] == "ACTIVE", (
            f"BatchJobIndex status is '{batch_index['IndexStatus']}', expected 'ACTIVE'"
        )
        
        # Check keys
        key_schema = batch_index["KeySchema"]
        partition_key = next(
            (k for k in key_schema if k["KeyType"] == "HASH"), None
        )
        
        assert partition_key["AttributeName"] == "batch_job_id"
        
        # Check projection
        assert batch_index["Projection"]["ProjectionType"] == "ALL"
        
        print("✓ BatchJobIndex exists with correct configuration")
        print("  - Key: batch_job_id (PK)")
        print("  - Projection: ALL")

    def test_user_index_configuration(self, dynamodb_client):
        """Test 6: Verify UserIndex GSI configuration"""
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        gsi_list = response["Table"].get("GlobalSecondaryIndexes", [])
        
        user_index = next(
            (idx for idx in gsi_list if idx["IndexName"] == "UserIndex"), None
        )
        assert user_index is not None, "UserIndex does not exist"
        assert user_index["IndexStatus"] == "ACTIVE", (
            f"UserIndex status is '{user_index['IndexStatus']}', expected 'ACTIVE'"
        )
        
        # Check keys
        key_schema = user_index["KeySchema"]
        partition_key = next(
            (k for k in key_schema if k["KeyType"] == "HASH"), None
        )
        sort_key = next(
            (k for k in key_schema if k["KeyType"] == "RANGE"), None
        )
        
        assert partition_key["AttributeName"] == "user_id"
        assert sort_key["AttributeName"] == "created_at"
        
        # Check projection
        assert user_index["Projection"]["ProjectionType"] == "ALL"
        
        print("✓ UserIndex exists with correct configuration")
        print("  - Keys: user_id (PK), created_at (SK)")
        print("  - Projection: ALL")

    def test_ttl_configuration(self, dynamodb_client):
        """Test 7: Verify TTL configuration"""
        try:
            response = dynamodb_client.describe_time_to_live(TableName=TABLE_NAME)
            ttl_desc = response["TimeToLiveDescription"]
            
            ttl_status = ttl_desc["TimeToLiveStatus"]
            assert ttl_status in ["ENABLED", "ENABLING"], (
                f"TTL status is '{ttl_status}', expected 'ENABLED' or 'ENABLING'"
            )
            
            if ttl_status == "ENABLED":
                ttl_attribute = ttl_desc["AttributeName"]
                assert ttl_attribute == "expiresAt", (
                    f"TTL attribute is '{ttl_attribute}', expected 'expiresAt'"
                )
                print("✓ TTL is enabled")
                print(f"  - TTL attribute: {ttl_attribute}")
            else:
                print("ℹ TTL is being enabled (status: ENABLING)")
                
        except ClientError as e:
            pytest.fail(f"Failed to describe TTL: {e}")

    @pytest.fixture
    def test_item(self, table):
        """Fixture: Create a test item and return its keys for other tests"""
        test_task_id = f"test-task-{int(datetime.now(timezone.utc).timestamp())}"
        test_created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        test_expires_at = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        
        item = {
            "task_id": test_task_id,
            "created_at": test_created_at,
            "status": "queued",
            "task_type": "test",
            "user_id": "test-user",
            "batch_job_id": f"test-batch-job-{int(datetime.now(timezone.utc).timestamp())}",
            "expiresAt": test_expires_at,
            "parameters": {},
        }
        
        # Write test item
        table.put_item(Item=item)
        print(f"✓ Created test item: {test_task_id}")
        
        # Yield the keys for tests to use
        yield test_task_id, test_created_at
        
        # Cleanup: Delete test item after tests
        try:
            table.delete_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
            print(f"✓ Cleaned up test item: {test_task_id}")
        except ClientError:
            pass  # Item may have been deleted by test

    def test_write_operation(self, table):
        """Test 8: Test basic write operation"""
        test_task_id = f"test-task-{int(datetime.now(timezone.utc).timestamp())}"
        test_created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        test_expires_at = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        
        item = {
            "task_id": test_task_id,
            "created_at": test_created_at,
            "status": "queued",
            "task_type": "test",
            "user_id": "test-user",
            "batch_job_id": f"test-batch-job-{int(datetime.now(timezone.utc).timestamp())}",
            "expiresAt": test_expires_at,
            "parameters": {},
        }
        
        try:
            table.put_item(Item=item)
            print(f"✓ Successfully wrote test item: {test_task_id}")
            
            # Cleanup
            table.delete_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
        except ClientError as e:
            pytest.fail(f"Failed to write test item: {e}")

    def test_read_operation(self, table, test_item):
        """Test 9: Test basic read operation"""
        test_task_id, test_created_at = test_item
        
        try:
            response = table.get_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
            
            assert "Item" in response, "Item not found"
            item = response["Item"]
            assert item["task_id"] == test_task_id
            assert item["status"] == "queued"
            
            print(f"✓ Successfully read test item: {test_task_id}")
        except ClientError as e:
            pytest.fail(f"Failed to read test item: {e}")

    def test_query_by_status(self, table, test_item):
        """Test 10: Test query by status using StatusIndex"""
        test_task_id, test_created_at = test_item
        
        try:
            response = table.query(
                IndexName="StatusIndex",
                KeyConditionExpression="#status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": "queued"},
                Limit=10,
            )
            
            assert "Items" in response
            assert response["Count"] > 0, "Query returned 0 items"
            
            # Verify our test item is in the results
            found = any(item["task_id"] == test_task_id for item in response["Items"])
            assert found, "Test item not found in query results"
            
            print(f"✓ Successfully queried by status (found {response['Count']} items)")
        except ClientError as e:
            pytest.fail(f"Failed to query by status: {e}")

    def test_query_by_batch_job_id(self, table, test_item):
        """Test 11: Test query by batch_job_id using BatchJobIndex"""
        test_task_id, test_created_at = test_item
        
        # Get the batch_job_id from the test item
        response = table.get_item(
            Key={
                "task_id": test_task_id,
                "created_at": test_created_at,
            }
        )
        batch_job_id = response["Item"]["batch_job_id"]
        
        try:
            response = table.query(
                IndexName="BatchJobIndex",
                KeyConditionExpression="batch_job_id = :batch_job_id",
                ExpressionAttributeValues={":batch_job_id": batch_job_id},
            )
            
            assert "Items" in response
            assert response["Count"] > 0, "Query returned 0 items"
            
            # Verify our test item is in the results
            found = any(item["task_id"] == test_task_id for item in response["Items"])
            assert found, "Test item not found in query results"
            
            print(f"✓ Successfully queried by batch_job_id (found {response['Count']} items)")
        except ClientError as e:
            pytest.fail(f"Failed to query by batch_job_id: {e}")

    def test_update_operation(self, table, test_item):
        """Test 12: Test basic update operation"""
        test_task_id, test_created_at = test_item
        
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
            
            # Verify update
            response = table.get_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
            
            assert response["Item"]["status"] == "completed"
            assert "updated_at" in response["Item"]
            
            print(f"✓ Successfully updated test item: {test_task_id}")
        except ClientError as e:
            pytest.fail(f"Failed to update test item: {e}")

    def test_delete_operation(self, table, test_item):
        """Test 13: Test basic delete operation"""
        test_task_id, test_created_at = test_item
        
        try:
            table.delete_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
            
            # Verify deletion
            response = table.get_item(
                Key={
                    "task_id": test_task_id,
                    "created_at": test_created_at,
                }
            )
            
            assert "Item" not in response, "Item still exists after deletion"
            
            print(f"✓ Successfully deleted test item: {test_task_id}")
        except ClientError as e:
            pytest.fail(f"Failed to delete test item: {e}")


if __name__ == "__main__":
    """Run tests directly"""
    print("=" * 50)
    print("DynamoDB Database Verification Tests")
    print("=" * 50)
    print(f"Environment: {ENVIRONMENT}")
    print(f"Table Name: {TABLE_NAME}")
    print(f"Region: {REGION}")
    print()
    
    pytest.main([__file__, "-v", "-s"])
