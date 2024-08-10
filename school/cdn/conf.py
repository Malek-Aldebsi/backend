import os

AWS_ACCESS_KEY_ID = 'DO00A8Y6226MQR86ACYM'
AWS_SECRET_ACCESS_KEY = 'UB6BkTS0SadRwkICIC8o+Z9OzskEPYFsFMhdH7eg4KI'
AWS_STORAGE_BUCKET_NAME = 'kawkab-spaces'
AWS_S3_ENDPOINT_URL = 'https://nyc3.digitaloceanspaces.com'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

AWS_LOCATION = 'https://kawkab-spaces.nyc3.digitaloceanspaces.com'

DEFAULT_FILE_STORAGE = 'school.cdn.backends.MediaRootS3Boto3Storage'
STATICFILES_STORAGE = 'school.cdn.backends.StaticRootS3Boto3Storage'
