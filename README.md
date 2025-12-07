# Message Search Engine API

A high-performance search engine API built with FastAPI that provides fast, paginated search results from an external messages data source.

## Features

- **Fast Search**: Sub-100ms response times through intelligent caching
- **Pagination**: Efficient pagination support for large result sets
- **Case-Insensitive Search**: Searches message content case-insensitively
- **Async Operations**: Built on async/await for optimal performance
- **Caching**: In-memory caching to minimize external API calls

## API Endpoints

### GET `/search`

Search messages by query string.

**Query Parameters:**
- `q` (required): Search query string (minimum 1 character)
- `page` (optional): Page number, defaults to 1
- `page_size` (optional): Number of items per page, defaults to 20 (max 100)

**Example Request:**
```bash
curl "http://localhost:8000/search?q=paris&page=1&page_size=20"
```

**Example Response:**
```json
{
  "total": 15,
  "items": [
    {
      "id": "b1e9bb83-18be-4b90-bbb8-83b7428e8e21",
      "user_id": "cd3a350e-dbd2-408f-afa0-16a072f56d23",
      "user_name": "Sophia Al-Farsi",
      "timestamp": "2025-05-05T07:47:20.159073+00:00",
      "message": "Please book a private jet to Paris for this Friday."
    }
  ],
  "page": 1,
  "page_size": 20,
  "query": "paris",
  "response_time_ms": 45.23
}
```

### GET `/health`

Health check endpoint.

### GET `/`

Root endpoint with service information.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker Deployment

Build and run with Docker:

```bash
docker build -t message-search-engine .
docker run -p 8000:8000 message-search-engine
```

## Performance Optimization

The service is optimized for sub-100ms response times through:

1. **In-Memory Caching**: Messages are cached for 60 seconds to avoid repeated API calls
2. **Async Operations**: Non-blocking async HTTP requests
3. **Efficient Filtering**: In-memory list comprehension for fast search
4. **Single API Fetch**: All messages fetched once and cached

## Design Notes: Alternative Approaches

### Approach 1: Direct API Proxy (Current Implementation)
**Pros:**
- Simple to implement
- Low memory footprint
- Easy to maintain
- Fast for small to medium datasets

**Cons:**
- Requires external API to be available
- Cache invalidation complexity
- Limited by external API performance

**Best for:** Small to medium datasets, when external API is reliable

### Approach 2: Full-Text Search with Elasticsearch/OpenSearch
**Pros:**
- Extremely fast search (sub-10ms possible)
- Advanced search features (fuzzy matching, relevance scoring)
- Scalable to millions of documents
- Built-in pagination and sorting

**Cons:**
- Requires additional infrastructure
- More complex setup and maintenance
- Higher resource usage
- Need to sync data from source

**Best for:** Large datasets, complex search requirements, production systems

### Approach 3: SQLite Full-Text Search (FTS5)
**Pros:**
- No external dependencies
- Fast search performance
- Lightweight and portable
- Built-in full-text indexing

**Cons:**
- Requires periodic data sync
- Limited scalability
- Single-file database can become bottleneck

**Best for:** Medium datasets, self-contained deployments

### Approach 4: Redis-Based Caching with Search
**Pros:**
- Very fast in-memory operations
- Distributed caching support
- Can use Redis Search module for advanced queries
- Better cache management

**Cons:**
- Requires Redis infrastructure
- Additional complexity
- Memory costs for large datasets

**Best for:** Distributed systems, high-traffic scenarios

### Approach 5: Pre-computed Search Index (Inverted Index)
**Pros:**
- Extremely fast lookups
- Can be stored in memory or on disk
- No external dependencies
- Predictable performance

**Cons:**
- Complex implementation
- Memory intensive for large vocabularies
- Requires index updates on data changes

**Best for:** Read-heavy workloads, specific use cases

## Data Insights: Reducing Latency to 30ms

To achieve 30ms response times, consider the following optimizations:

### 1. **Pre-load and Index Data**
Instead of fetching on-demand, pre-load all messages at startup and maintain an in-memory search index:
- **Impact**: Eliminates external API call latency (~50-100ms)
- **Trade-off**: Higher memory usage, slower startup time

### 2. **Use Trie or Inverted Index Data Structure**
Replace linear search with a pre-built index:
- **Trie**: Fast prefix matching, O(m) where m is query length
- **Inverted Index**: O(1) lookup for exact terms, very fast for keyword search
- **Impact**: Reduces search time from O(n) to O(m) or O(1)
- **Trade-off**: More complex implementation, higher memory usage

### 3. **Implement Response Caching**
Cache search results, not just raw data:
- Cache key: `(query, page, page_size)`
- **Impact**: Repeated queries return instantly (<1ms)
- **Trade-off**: Memory usage, cache invalidation complexity

### 4. **Use Faster Data Structures**
- Replace Python lists with NumPy arrays for filtering (if applicable)
- Use `set` operations for exact matches
- **Impact**: 2-3x faster filtering operations

### 5. **Parallel Processing**
- Use multiprocessing for filtering large datasets
- Split dataset into chunks and process in parallel
- **Impact**: 2-4x speedup on multi-core systems

### 6. **Optimize External API Calls**
- Use HTTP/2 connection pooling
- Implement request batching if API supports it
- Use compression (gzip) for responses
- **Impact**: Reduces network latency by 20-30%

### 7. **Database-Backed Solution**
If data changes infrequently:
- Store messages in PostgreSQL with full-text search (GIN index)
- Use connection pooling
- **Impact**: Sub-10ms queries possible with proper indexing

### 8. **CDN/Edge Caching**
For read-heavy workloads:
- Deploy at edge locations
- Use CDN caching for popular queries
- **Impact**: Geographic latency reduction

### Recommended Path to 30ms:

1. **Immediate (Current → ~50ms)**: Implement result caching for common queries
2. **Short-term (~30ms)**: Pre-load data at startup, use inverted index for search
3. **Long-term (<30ms)**: Move to Elasticsearch or PostgreSQL with FTS for production scale

### Example Implementation Sketch for 30ms:

```python
# Pre-built inverted index
from collections import defaultdict

class SearchIndex:
    def __init__(self):
        self.index = defaultdict(set)  # word -> set of message indices
        self.messages = []
    
    def build_index(self, messages):
        self.messages = messages
        for idx, msg in enumerate(messages):
            words = msg['message'].lower().split()
            for word in words:
                self.index[word].add(idx)
    
    def search(self, query):
        query_words = query.lower().split()
        if not query_words:
            return []
        
        # Find intersection of all query words
        result_indices = self.index[query_words[0]]
        for word in query_words[1:]:
            result_indices &= self.index[word]
        
        return [self.messages[idx] for idx in result_indices]
```

This approach can achieve <10ms search times for most queries.

## License

MIT

# message-search-engine
