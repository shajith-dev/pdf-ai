import boto3
from io import BytesIO
from urllib.parse import urlparse
import PyPDF2


class S3Util:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Util, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Initialize the boto3 S3 client only once.
        if not hasattr(self, 's3'):
            self.s3 = boto3.client('s3')

    @staticmethod
    def parse_s3_url(s3_url: str):
        """
        Parses an S3 URL and returns a tuple (bucket, key).
        Supports:
          - s3://bucket-name/path/to/object
          - https://bucket-name.s3.amazonaws.com/path/to/object
          - https://s3.amazonaws.com/bucket-name/path/to/object
        """
        # Case 1: s3://bucket/key
        if s3_url.startswith("s3://"):
            without_scheme = s3_url[5:]  # remove "s3://"
            parts = without_scheme.split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
            return bucket, key

        # Parse the URL for HTTP/HTTPS cases
        parsed = urlparse(s3_url)
        netloc = parsed.netloc
        path = parsed.path.lstrip("/")

        # Virtual-hosted–style: bucket-name.s3.amazonaws.com
        if netloc.endswith("amazonaws.com"):
            parts = netloc.split(".")
            # Path-style: https://s3.amazonaws.com/bucket/key
            if parts[0] == "s3":
                parts = path.split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""
                return bucket, key
            else:
                # Virtual-hosted–style: bucket-name.s3.amazonaws.com
                bucket = parts[0]
                key = path
                return bucket, key

        # Fallback for unknown formats
        return None, None

    def get_object(self, s3_url: str):
        """
        Given an S3 URL, fetches the object and returns its content as bytes.
        """
        bucket, key = self.parse_s3_url(s3_url)
        if not bucket or not key:
            raise ValueError("Invalid S3 URL provided.")
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()

    def get_pdf_text(self, s3_url: str) -> str:
        """
        Reads a PDF file from S3 (via its URL) and returns its text content.
        """
        pdf_data = self.get_object(s3_url)
        pdf_stream = BytesIO(pdf_data)
        reader = PyPDF2.PdfReader(pdf_stream)
        text_content = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text
        return text_content
