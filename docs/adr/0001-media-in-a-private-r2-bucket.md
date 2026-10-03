# Media lives in a private R2 bucket

Uploaded files (imported statements, later) are personal financial documents.
Production stores them in a private Cloudflare R2 bucket through
`django-storages`' S3 backend, and they are only ever reached through
short-lived signed URLs issued against the R2 endpoint. There is no custom
domain and no public read, so no statement sits at a guessable address.

The production container has a read-only filesystem and is replaced on every
upgrade, so a media volume would be the one piece of state tied to the host.
Keeping media in R2 leaves the container stateless: the database is the
operator's own Postgres, and everything else is in the image.

## Consequences

- `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID` and
  `S3_SECRET_ACCESS_KEY` are required when `DEBUG=false`; Django refuses to
  start without them, so a misconfigured deploy fails on boot rather than on
  the first upload.
- With `DEBUG=true` they are optional and the local filesystem
  (`MEDIA_ROOT`) is used when no bucket is set, so development needs no R2
  credentials.
- `default_acl` is off because R2 rejects ACLs, and `file_overwrite` is off so
  an upload with an existing name gets a new name instead of replacing
  another statement.
- `compose.prod.yaml` has no media volume, and backups of uploaded files are
  the bucket's concern, not the host's.
