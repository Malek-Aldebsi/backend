import os

AWS_ACCESS_KEY_ID = 'DO00NVEGTX3QUAF8MQGR'
AWS_SECRET_ACCESS_KEY = 'QxgdSpONWgrWKyJtGQGrjIzyeIcQccNQybY87XhU42s'
AWS_STORAGE_BUCKET_NAME = 'kawkab-space'
AWS_S3_ENDPOINT_URL = 'https://nyc3.digitaloceanspaces.com'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

AWS_LOCATION = 'https://kawkab-space.nyc3.digitaloceanspaces.com'

DEFAULT_FILE_STORAGE = 'school.cdn.backends.MediaRootS3Boto3Storage'
STATICFILES_STORAGE = 'school.cdn.backends.StaticRootS3Boto3Storage'
