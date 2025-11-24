# Technical Documentation: plugin.video.sosac.ph

## Overview

**plugin.video.sosac.ph** is a Kodi video add-on that provides access to movies and TV shows from sosac.tv (Czech/Slovak streaming service). The plugin allows users to browse, search, and play video content, as well as manage a personal library with subscription-based updates for TV shows.

### Key Features
- Browse movies and TV shows by categories (A-Z, genres, popularity)
- Search functionality for content discovery
- Library integration with automatic .strm file generation
- TV show subscriptions with automatic episode updates
- Multi-language support (Czech, Slovak, English)
- Dubbing/audio track filtering
- StreamujTV integration for premium content

---

## Architecture Overview

The plugin follows a classic **Provider-Presenter** pattern with three main layers:

```
┌─────────────────────────────────────────────┐
│            Kodi Interface Layer             │
│  (default.py, service.py)                   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Presentation Layer                  │
│  (XBMCSosac - sutils.py)                    │
│  - UI rendering                             │
│  - Library management                       │
│  - Subscription service                     │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│          Content Provider Layer             │
│  (SosacContentProvider - sosac.py)          │
│  - API communication                        │
│  - Content parsing                          │
│  - Stream resolution                        │
└─────────────────────────────────────────────┘
```

---

## File Structure

### Core Files

#### 1. **addon.xml**
- Kodi plugin manifest file
- Defines plugin metadata, dependencies, and requirements
- Requires Python 3.0.0+ (Kodi Matrix 19.x+)
- Dependencies:
  - `script.module.stream.resolver` - Stream URL resolution
  - `script.common.plugin.cache` - Caching functionality

#### 2. **default.py** (Main Entry Point)
- **Purpose**: Plugin entry point when user opens the add-on
- **Execution Flow**:
  ```python
  1. Parse URL parameters from sys.argv
  2. Load user settings from addon settings
  3. Initialize SosacContentProvider with configuration
  4. Create XBMCSosac presenter instance
  5. Call run() to handle the request
  ```
- **Key Settings Loaded**:
  - Episode ordering (newest/oldest first)
  - Force Czech language selection
  - Recently added sorting preference
  - StreamujTV credentials

#### 3. **service.py** (Background Service)
- **Purpose**: Runs as a Kodi background service
- **Functionality**:
  - Monitors TV show subscriptions
  - Automatically checks for new episodes (every 10 minutes)
  - Updates library with new content
  - Runs independently of the main plugin

---

## Core Components

### 1. SosacContentProvider (resources/lib/sosac.py)

**Responsibility**: Content fetching and data transformation

#### Key Methods:

##### **categories()** → List main menu items
```python
Returns:
- Movies (A-Z)
- TV Shows (A-Z)
- Movies by Genres
- Movies - Most Popular
- TV Shows - Most Popular
- Movies - Recently Added
- TV Shows - Recently Added
```

##### **search(keyword)** → Search content
- Validates keyword length (3-100 chars)
- Uses JSON search API: `/jsonsearchapi.php?q={keyword}`
- Returns video items matching search query

##### **list(url, filter)** → Route requests to appropriate handlers
Decision tree:
```
if "?filter" in url:
    → list_movies_by_dubbing()
elif "?dub=" in url:
    → list_dubbing()
elif J_MOVIES_A_TO_Z_TYPE or J_MOVIES_GENRE:
    → load_json_list()
elif J_SERIES:
    → list_episodes()
elif J_TV_SHOWS:
    → list_series_letter()
elif J_TV_SHOWS_RECENTLY_ADDED:
    → list_recentlyadded_episodes()
else:
    → list_videos()
```

##### **list_videos(url, filter, order_by)** → Parse movie listings
- Fetches JSON data from API
- Transforms JSON to Kodi video items
- Adds metadata: title, year, rating, quality, language, plot
- Generates thumbnail URLs
- Creates context menu items for library management
- Supports sorting by alpha or year

##### **list_series_letter(url)** → Parse TV show listings
- Similar to list_videos but for TV shows
- Checks subscription status
- Adds visual indicator (*) for subscribed shows
- Context menu for add/remove subscriptions

##### **list_episodes(url)** → Parse TV show episodes
- JSON structure: `[{season: {episode: video_data}}]`
- Formats episode titles: "01x05 - Episode Name"
- Can reverse episode order based on settings
- Returns episodes with season/episode metadata

##### **resolve(item, captcha_cb, select_cb)** → Get playable stream URL
Flow:
```
1. Extract video ID from item['url']
2. Construct StreamujTV URL
3. Call findstreams() (from parent class)
4. If multiple streams: let user select
5. Add StreamujTV credentials if configured
6. Call probe_html5() to resolve final URL
7. Return playable stream object
```

##### **probe_html5(result)** → Resolve HTML5 streams
- Creates custom HTTP redirect handler
- Prevents automatic redirects
- Extracts final stream URL from 302 response
- Returns resolved URL for Kodi player

#### JSON API Endpoints

```python
BASE_URL = "http://tv.sosac.to"

# Movies
/vystupy5981/souboryaz.json          # A-Z categories
/vystupy5981/souboryzanry.json       # Genres
/vystupy5981/moviesmostpopular.json  # Popular movies
/vystupy5981/moviesrecentlyadded.json # Recent movies

# TV Shows
/vystupy5981/tvpismenaaz/            # A-Z categories
/vystupy5981/tvpismena/{letter}.json # Shows by letter
/vystupy5981/serialy/{show_id}       # Episodes
/vystupy5981/tvshowsmostpopular.json # Popular shows
/vystupy5981/tvshowsrecentlyadded.json # Recent episodes

# Search
/jsonsearchapi.php?q={keyword}
```

#### Data Structures

**Movie JSON Object**:
```json
{
  "n": {"cs": "Název", "en": "Title"},  // Localized names
  "i": "12345",                          // Image ID
  "l": "video-link-id",                  // Link/Video ID
  "y": "2024",                           // Year
  "r": 4.5,                              // Rating (0-5)
  "d": ["cs", "en"],                     // Dubbing languages
  "q": "hd720",                          // Quality
  "g": ["Action", "Drama"],              // Genres
  "m": "1234567",                        // IMDB ID
  "c": "123456"                          // CSFD ID
}
```

**Episode JSON Object**:
```json
{
  "1": {                  // Season number
    "1": {                // Episode number
      "n": "Episode Name",
      "i": "/path/to/image.jpg",
      "l": "video-link-id"
    }
  }
}
```

---

### 2. XBMCSosac (resources/lib/sutils.py)

**Responsibility**: Kodi integration, UI rendering, library management

#### Key Methods:

##### **run(params)** → Main execution handler
- Inherited from XBMCMultiResolverContentProvider
- Routes requests based on params
- Calls run_custom() for library actions

##### **run_custom(params)** → Handle library operations

**Actions**:
1. **add-to-library**: Add single item to library
2. **remove-subscription**: Remove TV show subscription
3. **add-all-to-library**: Batch add all items
4. **remove-all-from-library**: Clear all subscriptions

##### **add_item(params)** → Add item to library

**For Movies** (LIBRARY_TYPE_VIDEO):
```
1. Get library path from settings
2. Create directory: {library}/normalized_name/
3. Create .nfo file with metadata (IMDB/CSFD links)
4. Create .strm file with plugin:// URL
5. Return success status
```

**For TV Shows** (LIBRARY_TYPE_TVSHOW):
```
1. Store subscription in cache
2. Create show directory
3. Create tvshow.nfo with metadata + TVDB ID
4. Fetch all episodes via provider.list_episodes()
5. For each episode:
   - Create Season N directory
   - Create S01E05.strm file with plugin URL
6. Track new vs existing files
7. Trigger Kodi library update if new content
```

##### **service()** → Background subscription monitor

**Flow**:
```python
1. Initialize xbmc.Monitor()
2. Sleep for configured start_sleep_time (default: 10 hours)
3. Load last_run timestamp from cache
4. Main loop (runs until Kodi shutdown):
   a. Every 10 minutes:
      - Call evalSchedules()
      - Update last_run timestamp
   b. Sleep 1 minute
   c. Check monitor.abortRequested()
```

##### **evalSchedules()** → Process subscription updates

**Logic**:
```python
1. Skip if library scan running or video playing
2. Load all subscriptions from cache
3. For each TV show subscription:
   a. Check if refresh interval elapsed
   b. If yes:
      - Show "Checking" notification
      - Re-add show to library (updates episodes)
      - Sleep 3 seconds (rate limiting)
   c. If no: skip to next
4. If new items found: trigger library update
```

**Refresh Calculation**:
```python
next_check = last_run + (refresh_days * 86400)
if time.now() > next_check:
    update_subscription()
```

##### **getTVDB(name, id)** → Fetch TheTVDB ID

**Strategy** (tries in order):
1. Query by IMDB ID if available
2. Query by short name (without year) in Czech
3. Query by short name in all languages
4. Query by full name in Czech
5. Query by full name in all languages
6. Return None if not found

Used for better metadata scraping in Kodi library.

##### **add_item_to_library(item_path, item_url)** → Write .strm file

**Process**:
```python
1. Translate special:// paths to real paths
2. Create parent directory if missing
3. Check if .strm file already exists
4. If new:
   a. Create file
   b. Write plugin URL to file
   c. Return (error=False, new=True)
5. If exists:
   - Return (error=False, new=False)
```

**.strm File Format**:
```
plugin://plugin.video.sosac.ph/?play=video-id&cp=sosac.ph&title=Movie+Name
```

##### **get_subs() / set_subs()** → Subscription persistence

**Storage**:
- Uses cache system (script.common.plugin.cache)
- Key: "subscription-1"
- Format: Python dict serialized with repr()
- Deserialized with ast.literal_eval() (safe alternative to eval)

**Subscription Object**:
```python
{
  "http://tv.sosac.to/vystupy5981/serialy/show-id": {
    "name": "Show Name (2024)",
    "type": "tvshow",
    "refresh": "1",        # Days between updates
    "last_run": 1700000000 # Unix timestamp
  }
}
```

##### **encode(string)** → String normalization

**Purpose**: Convert Unicode to ASCII for filesystem safety

**Process**:
```python
1. Handle bytes → str conversion
2. Apply NFKD normalization (decompose accents)
3. Encode to ASCII (ignore non-ASCII chars)
4. Decode back to str
Example: "Česká" → "Ceska"
```

##### **sleep(sleep_time, monitor)** → Interruptible sleep

**Modern Implementation**:
```python
# Old (deprecated):
while not xbmc.abortRequested and sleep_time > 0:
    xbmc.sleep(1)
    sleep_time -= 1

# New (Python 3):
monitor.waitForAbort(sleep_time / 1000.0)
```
- Converts milliseconds to seconds
- Can be interrupted by Kodi shutdown
- More efficient (single system call)

---

## Data Flow Diagrams

### 1. User Browses Movies

```
User clicks "Movies"
    ↓
default.py receives params={}
    ↓
XBMCSosac.run(params)
    ↓
SosacContentProvider.categories()
    ↓
Returns menu items
    ↓
User clicks "Movies - Most Popular"
    ↓
default.py receives params={url: "...moviesmostpopular.json"}
    ↓
SosacContentProvider.list(url)
    ↓
SosacContentProvider.list_videos(url)
    ↓
HTTP GET http://tv.sosac.to/vystupy5981/moviesmostpopular.json
    ↓
Parse JSON → Create video items
    ↓
XBMCSosac renders items in Kodi UI
    ↓
User selects movie
    ↓
SosacContentProvider.resolve(item)
    ↓
findstreams() → probe_html5()
    ↓
Return playable URL
    ↓
Kodi plays video
```

### 2. Add TV Show to Library

```
User browses to TV Show
    ↓
Right-click → "Add to library"
    ↓
XBMCSosac.run_custom({
  action: "add-to-library",
  type: "tvshow",
  url: "show-url",
  name: "Show Name"
})
    ↓
XBMCSosac.add_item(params)
    ↓
Store subscription in cache
    ↓
SosacContentProvider.list_episodes(url)
    ↓
HTTP GET http://tv.sosac.to/vystupy5981/serialy/show-id
    ↓
Parse episodes JSON
    ↓
For each episode:
    ├─ Create directory: TVShows/Show-Name/Season 1/
    └─ Write file: S01E05.strm
    ↓
Show notification: "Found new content"
    ↓
Trigger xbmc.executebuiltin('UpdateLibrary(video)')
    ↓
Kodi scans .strm files
    ↓
Episodes appear in library
```

### 3. Background Service Updates Subscription

```
service.py starts
    ↓
XBMCSosac.service()
    ↓
Wait start_sleep_time (10 hours default)
    ↓
Main loop starts
    ↓
Every 10 minutes:
    ↓
XBMCSosac.evalSchedules()
    ↓
Load subscriptions from cache
    ↓
For each subscription:
    ├─ Calculate: next_check = last_run + (refresh_days * 86400)
    ├─ If time.now() > next_check:
    │   ├─ Show notification: "Checking"
    │   ├─ XBMCSosac.add_item(subscription)
    │   │   ↓
    │   │   SosacContentProvider.list_episodes()
    │   │   ↓
    │   │   Compare existing .strm files with API response
    │   │   ↓
    │   │   Create new .strm files for new episodes
    │   │   ↓
    │   │   Return new_items=True
    │   ├─ Update last_run timestamp
    │   └─ Sleep 3 seconds
    └─ Else: skip
    ↓
If any new_items:
    ↓
xbmc.executebuiltin('UpdateLibrary(video)')
    ↓
Sleep 1 minute
    ↓
Loop continues until Kodi shutdown
```

---

## Settings Configuration

### User Settings (resources/settings.xml)

**Category: General**
- `streamujtv_user` - StreamujTV username
- `streamujtv_pass` - StreamujTV password (hidden)
- `streamujtv_location` - Server location preference
- `keep-searches` - Number of searches to keep in history
- `subs` - Enable subtitles
- `order-episodes` - Episode order (newest/oldest first)
- `quality` - Preferred video quality
- `language` - Interface language
- `force-czech` - Force Czech language selection
- `order-recently-by` - Sort recently added by (date/name/year)
- `downloads` - Download folder path
- `download-notify` - Show download notifications
- `download-notify-every` - Notification frequency

**Category: Library**
- `library-movies` - Movies library path
- `library-tvshows` - TV Shows library path
- `start_sleep_time` - Service start delay (0-60 hours)
- `refresh_time` - Subscription refresh interval (0-60 days)

---

## URL Routing & Parameters

### Plugin URL Structure

```
plugin://plugin.video.sosac.ph/?param1=value1&param2=value2
```

### Common Parameters

- **No params** (`{}`): Show main categories
- **`url`**: List content from URL
- **`play`**: Video ID to play
- **`action`**: Library action (add-to-library, remove-subscription, etc.)
- **`type`**: Content type (video, tvshow, all-videos, etc.)
- **`name`**: Item name for library
- **`refresh`**: Refresh interval for subscriptions
- **`imdb`**: IMDB ID for metadata
- **`csfd`**: CSFD ID for metadata

### Example URLs

```
# Main menu
plugin://plugin.video.sosac.ph/

# Browse movies A-Z
plugin://plugin.video.sosac.ph/?url=http://tv.sosac.to/vystupy5981/souboryaz.json

# Play video
plugin://plugin.video.sosac.ph/?play=video-123&cp=sosac.ph&title=Movie+Name

# Add to library
plugin://plugin.video.sosac.ph/?action=add-to-library&type=tvshow&url=show-url&name=Show+Name
```

---

## Caching Strategy

### Cache Provider
- Uses `script.common.plugin.cache` (StorageServer)
- Fallback to dummy cache if unavailable

### Cached Data
1. **Subscriptions** (`subscription-1`)
   - TV show subscriptions and settings
   - Persisted across Kodi restarts

2. **Last Run Timestamp** (`subscription.last_run`)
   - Tracks last subscription check time
   - Prevents duplicate checks on restart

### Cache Operations
```python
# Store
self.cache.set(key, value)

# Retrieve
data = self.cache.get(key)

# Delete
self.cache.delete(key)
```

---

## Stream Resolution Process

### Multi-Step Resolution

1. **API Call**: Get video metadata from sosac.tv API
2. **StreamujTV URL**: Construct URL `http://www.streamuj.tv/video/{video_id}`
3. **findstreams()**: Parent class method resolves StreamujTV page
4. **Stream Selection**: If multiple qualities, user selects
5. **Credential Injection**: Add StreamujTV login if configured
6. **HTML5 Probe**: Follow redirects to get final .m3u8 or .mp4 URL
7. **Return to Kodi**: Kodi player handles final URL

### StreamujTV Authentication

```python
if user and password:
    md5_pass = md5(md5(password))
    url += "&pass={user}:::{md5_pass}"
if location:
    url += "&location={location}"
```

---

## Error Handling

### Network Errors
- HTTP errors caught with `urllib.error.HTTPError`
- Errors logged via `util.error()`
- User shown empty list or error dialog

### File System Errors
- Directory creation wrapped in try/except
- .strm file write failures logged
- User notification: "Failed, Please check kodi logs"

### JSON Parsing
- Invalid JSON returns empty list
- Malformed data skipped, processing continues

### Graceful Degradation
- Missing metadata fields use defaults
- Missing images show placeholder
- Failed stream resolution shows error message

---

## Localization

### Language Support
- Czech (cs)
- Slovak (sk)
- English (en)

### String Files
- `resources/language/{Language}/strings.xml`
- Loaded via `__addon__.getLocalizedString(id)`

### Content Localization
- API returns multi-language titles: `{"cs": "Název", "en": "Title"}`
- Plugin selects based on Kodi language setting
- Fallback to Czech if language not available

---

## Security Considerations

### Input Validation
- Search keyword length checked (3-100 chars)
- URL parameters sanitized before use

### Safe Deserialization
- **Old**: `eval(data)` - arbitrary code execution risk
- **New**: `ast.literal_eval(data)` - only evaluates literals

### Credential Handling
- Passwords hashed (MD5) before transmission
- Stored in Kodi settings (encrypted by Kodi)

### File System Safety
- Filename normalization removes special chars
- Path traversal prevented by using safe path joins
- xbmcvfs API provides sandboxed file access

---

## Performance Optimizations

### Lazy Loading
- Content fetched only when user navigates to section
- Episodes loaded on-demand per show

### Batch Operations
- "Add all to library" with progress dialog
- Prevents UI freezing on large operations

### Rate Limiting
- 3-second sleep between subscription updates
- Prevents API hammering

### Monitor-based Sleep
- Single system call vs polling loop
- Lower CPU usage in background service

---

## Dependencies

### Required Kodi Modules
- `xbmc` - Core Kodi functionality
- `xbmcaddon` - Addon settings and info
- `xbmcgui` - UI dialogs and windows
- `xbmcvfs` - Virtual file system
- `xbmcutil` - Utility functions (from resolver)
- `xbmcprovider` - Base provider class (from resolver)

### Required Add-ons
- `script.module.stream.resolver` - Stream URL resolution
- `script.common.plugin.cache` - Persistent caching

### Python Standard Library
- `urllib.request`, `urllib.parse` - HTTP requests
- `http.cookiejar` - Cookie management
- `json` - JSON parsing
- `re` - Regular expressions
- `datetime` - Timestamp handling
- `hashlib` - MD5 hashing
- `ast` - Safe literal evaluation

---

## Migration Notes (Python 2 → Python 3)

### Breaking Changes Fixed
1. `urllib2` → `urllib.request`
2. `cookielib` → `http.cookiejar`
3. `dict.iteritems()` → `dict.items()`
4. `except E, e:` → `except E as e:`
5. `str.decode('utf-8')` → handled in Python 3 natively
6. `xbmc.abortRequested` → `xbmc.Monitor().abortRequested()`
7. `xbmc.sleep()` → `xbmc.Monitor().waitForAbort()`
8. `xbmc.translatePath()` → `xbmcvfs.translatePath()`

### Compatibility
- Requires Kodi Matrix (19.x) or later
- Python 3.6+ recommended
- No Python 2 support

---

## Testing Recommendations

### Manual Tests
1. Browse categories (Movies, TV Shows)
2. Search for content
3. Play video
4. Add movie to library
5. Add TV show to library
6. Check subscription updates
7. Test dubbing filter
8. Verify settings changes

### Edge Cases
- Empty search results
- Invalid video IDs
- Network timeouts
- Full disk (library)
- Concurrent library scans
- Service restart during update

### Integration Tests
- Library scanner recognition of .strm files
- Metadata scraper integration (IMDB/TVDB)
- Multi-language UI switching
- Settings persistence

---

## Future Enhancement Possibilities

### Code Quality
- Add type hints (Python 3.5+)
- Split large methods into smaller units
- Add docstrings to all methods
- Implement proper logging levels

### Features
- Resume watching functionality
- Watched status tracking
- Favorites/bookmarks
- Download queue management
- Subtitle auto-download
- Multiple audio track selection

### Architecture
- Async/await for API calls (aiohttp)
- Better separation of concerns
- Unit test coverage
- CI/CD integration
- Settings v2 format migration

### Performance
- Response caching with TTL
- Thumbnail pre-loading
- Lazy episode loading (pagination)
- Database for subscription tracking

---

## Troubleshooting Guide

### Plugin Not Loading
- Check Kodi version (≥19.x required)
- Verify dependencies installed
- Check kodi.log for errors

### No Videos Playing
- Check stream.resolver version
- Test StreamujTV credentials
- Verify internet connection
- Check firewall/proxy settings

### Library Not Updating
- Check service.py is running
- Verify library paths writable
- Check subscription refresh settings
- Review kodi.log for errors

### Search Not Working
- Clear addon cache
- Check keyword length (3-100 chars)
- Verify API accessibility
- Test with simple search term

---

## License

GNU General Public License v2.0 or later

## Authors

- Libor Zoubek (original author)
- jondas (co-maintainer)
- BBaronSVK (library features)
- Community contributors

---

**Last Updated**: 2024 (Python 3 Refactoring)
