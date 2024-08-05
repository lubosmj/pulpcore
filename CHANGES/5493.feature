Optimized replication to skip syncing when upstream distributions are unchanged. This uses the new
`content_last_updated` field on the distribution serializer to track content source timestamps.
