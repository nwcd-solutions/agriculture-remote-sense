"""
S3 Storage Service for managing file uploads, downloads, and presigned URLs.
"""
import os
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for interacting with AWS S3 storage."""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-west-2",
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize S3 storage service.
        
        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region (default: us-west-2)
            endpoint_url: Optional endpoint URL for local testing (e.g., LocalStack)
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url
        )
        
        logger.info(f"Initialized S3StorageService for bucket: {bucket_name}")
    
    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3.
        
        Args:
            local_path: Path to the local file
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach to the object
            
        Returns:
            S3 URL of the uploaded file
            
        Raises:
            FileNotFoundError: If local file doesn't exist
            ClientError: If S3 upload fails
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded file to {s3_url}")
            
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
    
    def download_file(
        self,
        s3_key: str,
        local_path: str
    ) -> str:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
            local_path: Path where to save the downloaded file
            
        Returns:
            Path to the downloaded file
            
        Raises:
            ClientError: If S3 download fails
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            logger.info(f"Downloaded file from s3://{self.bucket_name}/{s3_key} to {local_path}")
            
            return local_path
            
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        http_method: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for temporary access to an S3 object.
        
        Args:
            s3_key: S3 object key (path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method ('get_object' or 'put_object')
            
        Returns:
            Presigned URL
            
        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if deletion was successful
            
        Raises:
            ClientError: If S3 deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Deleted file: s3://{self.bucket_name}/{s3_key}")
            
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise
    
    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[str]:
        """
        List files in S3 bucket with optional prefix filter.
        
        Args:
            prefix: Prefix to filter objects (default: empty string)
            max_keys: Maximum number of keys to return (default: 1000)
            
        Returns:
            List of S3 object keys
            
        Raises:
            ClientError: If S3 list operation fails
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' not in response:
                return []
            
            keys = [obj['Key'] for obj in response['Contents']]
            
            logger.info(f"Listed {len(keys)} files with prefix: {prefix}")
            
            return keys
            
        except ClientError as e:
            logger.error(f"Failed to list files from S3: {e}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_size(self, s3_key: str) -> int:
        """
        Get the size of a file in S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            File size in bytes
            
        Raises:
            ClientError: If file doesn't exist or operation fails
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['ContentLength']
        except ClientError as e:
            logger.error(f"Failed to get file size: {e}")
            raise
