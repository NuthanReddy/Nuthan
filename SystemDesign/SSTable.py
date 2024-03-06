# keep a map of key to data location in memory

# as key values come, and not greater than the max size, keep adding to the memstore
# when the memstore is full, write to disk

# when reading, check the memstore first, then the disk
# the size of ss table is small such that the search is fast

# compaction is done based on multiple policies, slab based or time based or size based or a combination of these
# the compaction is done in the background, and the read and write operations are not blocked


