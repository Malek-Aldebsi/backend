import os

AWS_ACCESS_KEY_ID = 'DO00FWFP77FK2NRZ2R72'
AWS_SECRET_ACCESS_KEY = 'DAAJC3hIKhzJ8QnD/8tb0YYQ5cD+eA3BtHnp4TpbBUM'
AWS_STORAGE_BUCKET_NAME = 'kawkab'
AWS_S3_ENDPOINT_URL = 'https://nyc3.digitaloceanspaces.com'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

AWS_LOCATION = 'https://kawkab-space.nyc3.digitaloceanspaces.com'

DEFAULT_FILE_STORAGE = 'school.cdn.backends.MediaRootS3Boto3Storage'
STATICFILES_STORAGE = 'school.cdn.backends.StaticRootS3Boto3Storage'
