"""
AWS Lambda handler for FastAPI application
"""
import os
from mangum import Mangum
from main import app

# Create Lambda handler
handler = Mangum(app, lifespan="off")
