# FinAgent Plugin Architecture
**Extensible Platform & Content System**

---

## Philosophy

**"Everything is a Plugin"**

Instead of hardcoding Twitter, LinkedIn, and Newsletter, we build a plugin system where:
- ✅ Platforms are plugins (Twitter, LinkedIn, Newsletter, Future platforms)
- ✅ Each plugin defines its own content format, size, and rules
- ✅ Adding a new platform = creating a new plugin (no core code changes)
- ✅ Plugins can be enabled/disabled independently
- ✅ Each plugin handles its own generation, validation, and publishing

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      PLUGIN REGISTRY                             │
│            (Discovers, Loads, Manages Plugins)                  │
└─────────────────────────────────────────────────────────────────┘
                              |
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                 ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Twitter    │  │  LinkedIn    │  │ Newsletter   │
    │   Plugin     │  │   Plugin     │  │   Plugin     │
    └──────────────┘  └──────────────┘  └──────────────┘
            |                 |                 |
    ┌───────┴───────┐ ┌───────┴───────┐ ┌───────┴───────┐
    ↓       ↓       ↓ ↓       ↓       ↓ ↓       ↓       ↓
Generator Validator Publisher Generator Validator Publisher ...
```

---

## Plugin Interface

### Base Plugin Class

```python
# plugins/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel

class ContentFormat(BaseModel):
    """Defines the content format for a platform."""
    name: str  # "thread", "single_post", "article", etc.
    max_length: Optional[int]  # Character limit (None = unlimited)
    min_length: Optional[int]  # Minimum characters
    supports_html: bool
    supports_markdown: bool
    supports_images: bool
    supports_videos: bool
    max_items: Optional[int]  # For threads/carousels
    metadata: Dict  # Additional format-specific config

class PlatformPlugin(ABC):
    """Base class for all platform plugins."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Unique platform identifier (e.g., 'twitter', 'linkedin')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable platform name (e.g., 'Twitter', 'LinkedIn')."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> List[ContentFormat]:
        """List of content formats this platform supports."""
        pass

    @property
    def enabled(self) -> bool:
        """Is this plugin currently enabled?"""
        return True

    @property
    def requires_auth(self) -> bool:
        """Does this platform require authentication?"""
        return True

    # === Content Generation ===

    @abstractmethod
    def generate_content(
        self,
        raw_output: str,
        event_type: str,
        metadata: Dict
    ) -> Dict:
        """
        Transform raw LLM output into platform-specific content.

        Args:
            raw_output: Original LLM explanation (200-400 words)
            event_type: Type of event (FINANCE_POLICY, MARKET_MOVEMENT, etc.)
            metadata: Additional context (source, date, etc.)

        Returns:
            Dict with platform-specific content structure
        """
        pass

    # === Validation ===

    @abstractmethod
    def validate_content(self, content_data: Dict) -> tuple[bool, List[str]]:
        """
        Validate generated content meets platform requirements.

        Returns:
            (is_valid, list_of_errors)
        """
        pass

    # === Publishing ===

    @abstractmethod
    def publish(
        self,
        content_data: Dict,
        credentials: Dict
    ) -> Dict:
        """
        Publish content to the platform.

        Returns:
            {
                "success": bool,
                "platform_id": str,  # External post ID
                "platform_url": str,  # Direct link to post
                "error": Optional[str]
            }
        """
        pass

    # === Analytics ===

    @abstractmethod
    def fetch_analytics(
        self,
        platform_id: str,
        credentials: Dict
    ) -> Dict:
        """
        Fetch engagement metrics for published content.

        Returns:
            {
                "impressions": int,
                "engagements": int,
                "clicks": int,
                "likes": int,
                "shares": int,
                "comments": int,
                ...
            }
        """
        pass

    # === Configuration ===

    @abstractmethod
    def get_auth_config(self) -> Dict:
        """
        Return authentication configuration requirements.

        Returns:
            {
                "type": "oauth" | "api_key" | "credentials",
                "fields": [
                    {"name": "api_key", "type": "string", "required": True},
                    ...
                ]
            }
        """
        pass

    # === Optimal Timing ===

    def get_optimal_posting_times(self) -> List[Dict]:
        """
        Return optimal posting times for this platform (IST timezone).

        Returns:
            [
                {"day": "monday", "hour": 9, "minute": 0},
                {"day": "tuesday", "hour": 14, "minute": 30},
                ...
            ]
        """
        return []

    # === Preview ===

    def generate_preview_html(self, content_data: Dict) -> str:
        """
        Generate HTML preview of how content will look on platform.

        Returns:
            HTML string for rendering in dashboard
        """
        return "<div>Preview not available</div>"
```

---

## Example Plugin: Twitter

```python
# plugins/twitter_plugin.py

from typing import Dict, List
from plugins.base import PlatformPlugin, ContentFormat
from llm.client import LLMClient
import tweepy

class TwitterPlugin(PlatformPlugin):
    """Twitter (X) platform plugin."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    def platform_name(self) -> str:
        return "twitter"

    @property
    def display_name(self) -> str:
        return "Twitter (X)"

    @property
    def supported_formats(self) -> List[ContentFormat]:
        return [
            ContentFormat(
                name="thread",
                max_length=280,  # Per tweet
                min_length=10,
                supports_html=False,
                supports_markdown=False,
                supports_images=True,
                supports_videos=True,
                max_items=5,  # Max 5 tweets in thread
                metadata={
                    "max_hashtags": 3,
                    "emoji_allowed": True,
                    "thread_indicators": ["🧵", "👇", "↓"]
                }
            ),
            ContentFormat(
                name="single_tweet",
                max_length=280,
                min_length=10,
                supports_html=False,
                supports_markdown=False,
                supports_images=True,
                supports_videos=True,
                max_items=1,
                metadata={
                    "max_hashtags": 3,
                    "emoji_allowed": True
                }
            )
        ]

    def generate_content(
        self,
        raw_output: str,
        event_type: str,
        metadata: Dict
    ) -> Dict:
        """Generate Twitter thread from raw output."""

        prompt = f"""
Transform this finance explanation into a Twitter thread (3-5 tweets).

Original Content:
{raw_output}

Event Type: {event_type}
Source: {metadata.get('source', 'Unknown')}

Requirements:
- Create 3-5 tweets
- Each tweet max 260 characters (leave room for hashtags)
- Tweet 1: Hook with emoji (grab attention)
- Tweet 2: Context (what happened)
- Tweet 3: Impact (what it means - bullet points)
- Tweet 4: Education (explain key concept simply)
- Tweet 5: CTA (link placeholder)
- Use 2-3 relevant hashtags in last tweet only
- Add thread indicator (🧵 or 👇) in first tweet
- Keep calm, educational tone
- NO advice, NO predictions

Output as JSON:
{{
  "format": "thread",
  "tweets": [
    {{"order": 1, "text": "Tweet 1 text here"}},
    {{"order": 2, "text": "Tweet 2 text here"}},
    ...
  ],
  "hashtags": ["Finance", "RBI"],
  "total_count": 5
}}
"""

        response = self.llm.generate(prompt)
        content_data = self._parse_json(response)

        return content_data

    def validate_content(self, content_data: Dict) -> tuple[bool, List[str]]:
        """Validate Twitter content."""
        errors = []

        if content_data.get("format") != "thread":
            errors.append("Invalid format: expected 'thread'")

        tweets = content_data.get("tweets", [])

        if len(tweets) < 3 or len(tweets) > 5:
            errors.append(f"Thread must have 3-5 tweets, got {len(tweets)}")

        for tweet in tweets:
            text = tweet.get("text", "")
            if len(text) > 280:
                errors.append(f"Tweet {tweet['order']} exceeds 280 chars: {len(text)}")
            if len(text) < 10:
                errors.append(f"Tweet {tweet['order']} too short: {len(text)}")

        # Check for forbidden language
        forbidden = ["buy", "sell", "should invest", "guaranteed", "must act"]
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            for word in forbidden:
                if word in text:
                    errors.append(f"Forbidden word '{word}' in tweet {tweet['order']}")

        # Check hashtags
        hashtags = content_data.get("hashtags", [])
        if len(hashtags) > 3:
            errors.append(f"Too many hashtags: {len(hashtags)} (max 3)")

        return (len(errors) == 0, errors)

    def publish(self, content_data: Dict, credentials: Dict) -> Dict:
        """Publish thread to Twitter."""
        try:
            # Initialize Twitter client
            client = tweepy.Client(
                bearer_token=credentials.get("bearer_token"),
                consumer_key=credentials.get("api_key"),
                consumer_secret=credentials.get("api_secret"),
                access_token=credentials.get("access_token"),
                access_token_secret=credentials.get("access_token_secret")
            )

            tweets = content_data.get("tweets", [])
            hashtags = content_data.get("hashtags", [])

            # Add hashtags to last tweet
            if hashtags and tweets:
                tweets[-1]["text"] += "\n\n" + " ".join(f"#{tag}" for tag in hashtags)

            # Post thread
            previous_tweet_id = None
            first_tweet_id = None

            for tweet in tweets:
                response = client.create_tweet(
                    text=tweet["text"],
                    in_reply_to_tweet_id=previous_tweet_id
                )

                tweet_id = response.data["id"]

                if not first_tweet_id:
                    first_tweet_id = tweet_id

                previous_tweet_id = tweet_id

            return {
                "success": True,
                "platform_id": first_tweet_id,
                "platform_url": f"https://twitter.com/i/web/status/{first_tweet_id}",
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "platform_id": None,
                "platform_url": None,
                "error": str(e)
            }

    def fetch_analytics(self, platform_id: str, credentials: Dict) -> Dict:
        """Fetch Twitter analytics."""
        try:
            client = tweepy.Client(bearer_token=credentials.get("bearer_token"))

            tweet = client.get_tweet(
                platform_id,
                tweet_fields=["public_metrics"]
            )

            metrics = tweet.data.public_metrics

            return {
                "impressions": metrics.get("impression_count", 0),
                "engagements": (
                    metrics.get("like_count", 0) +
                    metrics.get("retweet_count", 0) +
                    metrics.get("reply_count", 0)
                ),
                "clicks": 0,  # Not available in basic API
                "likes": metrics.get("like_count", 0),
                "shares": metrics.get("retweet_count", 0),
                "comments": metrics.get("reply_count", 0),
                "bookmarks": metrics.get("bookmark_count", 0)
            }

        except Exception as e:
            return {"error": str(e)}

    def get_auth_config(self) -> Dict:
        """Twitter OAuth configuration."""
        return {
            "type": "oauth",
            "fields": [
                {"name": "api_key", "type": "string", "required": True},
                {"name": "api_secret", "type": "password", "required": True},
                {"name": "access_token", "type": "string", "required": True},
                {"name": "access_token_secret", "type": "password", "required": True},
                {"name": "bearer_token", "type": "password", "required": False}
            ]
        }

    def get_optimal_posting_times(self) -> List[Dict]:
        """Optimal Twitter posting times (IST)."""
        return [
            {"day": "monday", "hour": 9, "minute": 0},
            {"day": "monday", "hour": 13, "minute": 0},
            {"day": "monday", "hour": 18, "minute": 0},
            {"day": "tuesday", "hour": 9, "minute": 0},
            {"day": "tuesday", "hour": 13, "minute": 0},
            {"day": "wednesday", "hour": 9, "minute": 0},
            {"day": "thursday", "hour": 9, "minute": 0},
            {"day": "friday", "hour": 9, "minute": 0}
        ]

    def generate_preview_html(self, content_data: Dict) -> str:
        """Generate HTML preview of Twitter thread."""
        tweets = content_data.get("tweets", [])

        html_parts = ['<div class="twitter-preview space-y-3">']

        for tweet in tweets:
            html_parts.append(f'''
            <div class="border rounded-lg p-4 bg-white shadow-sm">
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
                        FA
                    </div>
                    <div class="flex-1">
                        <div class="font-bold">FinAgent</div>
                        <div class="text-sm text-gray-500">@finagent_ai</div>
                        <div class="mt-2 whitespace-pre-wrap">{tweet["text"]}</div>
                        <div class="mt-2 text-xs text-gray-400">
                            {len(tweet["text"])}/280 characters
                        </div>
                    </div>
                </div>
            </div>
            ''')

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _parse_json(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        import json
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
```

---

## Example Plugin: LinkedIn

```python
# plugins/linkedin_plugin.py

from typing import Dict, List
from plugins.base import PlatformPlugin, ContentFormat
from llm.client import LLMClient
import requests

class LinkedInPlugin(PlatformPlugin):
    """LinkedIn platform plugin."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    def platform_name(self) -> str:
        return "linkedin"

    @property
    def display_name(self) -> str:
        return "LinkedIn"

    @property
    def supported_formats(self) -> List[ContentFormat]:
        return [
            ContentFormat(
                name="single_post",
                max_length=3000,
                min_length=100,
                supports_html=False,
                supports_markdown=False,
                supports_images=True,
                supports_videos=True,
                max_items=1,
                metadata={
                    "max_hashtags": 5,
                    "emoji_allowed": True,
                    "professional_tone": True
                }
            ),
            ContentFormat(
                name="article",
                max_length=125000,  # LinkedIn articles
                min_length=500,
                supports_html=True,
                supports_markdown=False,
                supports_images=True,
                supports_videos=False,
                max_items=1,
                metadata={
                    "requires_title": True,
                    "supports_cover_image": True
                }
            )
        ]

    def generate_content(
        self,
        raw_output: str,
        event_type: str,
        metadata: Dict
    ) -> Dict:
        """Generate LinkedIn post from raw output."""

        prompt = f"""
Transform this finance explanation into a LinkedIn post.

Original Content:
{raw_output}

Event Type: {event_type}
Source: {metadata.get('source', 'Unknown')}

Requirements:
- Professional tone, informative
- 500-800 words
- Start with headline + emoji
- Use sections with emoji headers
- Include "What This Means for You" with bullet points
- Explain key concepts in simple terms
- End with bottom line summary
- Add 3-5 relevant hashtags at end
- Add link placeholder
- Keep calm, educational tone
- NO advice, NO predictions

Output as JSON:
{{
  "format": "single_post",
  "text": "Full LinkedIn post text here...",
  "hashtags": ["Finance", "RBI", "MonetaryPolicy"],
  "word_count": 650
}}
"""

        response = self.llm.generate(prompt)
        content_data = self._parse_json(response)

        return content_data

    def validate_content(self, content_data: Dict) -> tuple[bool, List[str]]:
        """Validate LinkedIn content."""
        errors = []

        text = content_data.get("text", "")

        if len(text) > 3000:
            errors.append(f"Post exceeds 3000 chars: {len(text)}")

        if len(text) < 100:
            errors.append(f"Post too short: {len(text)}")

        # Check for forbidden language
        forbidden = ["buy", "sell", "should invest", "guaranteed"]
        text_lower = text.lower()
        for word in forbidden:
            if word in text_lower:
                errors.append(f"Forbidden word '{word}' in post")

        # Check hashtags
        hashtags = content_data.get("hashtags", [])
        if len(hashtags) > 5:
            errors.append(f"Too many hashtags: {len(hashtags)} (max 5)")

        return (len(errors) == 0, errors)

    def publish(self, content_data: Dict, credentials: Dict) -> Dict:
        """Publish to LinkedIn."""
        try:
            access_token = credentials.get("access_token")
            person_urn = credentials.get("person_urn")

            text = content_data.get("text", "")
            hashtags = content_data.get("hashtags", [])

            # Add hashtags
            if hashtags:
                text += "\n\n" + " ".join(f"#{tag}" for tag in hashtags)

            url = "https://api.linkedin.com/v2/ugcPosts"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            post_id = response.headers.get("X-RestLi-Id")

            return {
                "success": True,
                "platform_id": post_id,
                "platform_url": f"https://www.linkedin.com/feed/update/{post_id}",
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "platform_id": None,
                "platform_url": None,
                "error": str(e)
            }

    def fetch_analytics(self, platform_id: str, credentials: Dict) -> Dict:
        """Fetch LinkedIn analytics."""
        try:
            access_token = credentials.get("access_token")

            url = f"https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity={platform_id}"

            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            stats = data.get("elements", [{}])[0]

            return {
                "impressions": stats.get("impressionCount", 0),
                "engagements": stats.get("engagement", 0),
                "clicks": stats.get("clickCount", 0),
                "likes": stats.get("likeCount", 0),
                "shares": stats.get("shareCount", 0),
                "comments": stats.get("commentCount", 0)
            }

        except Exception as e:
            return {"error": str(e)}

    def get_auth_config(self) -> Dict:
        """LinkedIn OAuth configuration."""
        return {
            "type": "oauth",
            "fields": [
                {"name": "access_token", "type": "password", "required": True},
                {"name": "person_urn", "type": "string", "required": True}
            ]
        }

    def get_optimal_posting_times(self) -> List[Dict]:
        """Optimal LinkedIn posting times (IST)."""
        return [
            {"day": "tuesday", "hour": 10, "minute": 0},
            {"day": "tuesday", "hour": 14, "minute": 0},
            {"day": "wednesday", "hour": 10, "minute": 0},
            {"day": "wednesday", "hour": 14, "minute": 0},
            {"day": "thursday", "hour": 10, "minute": 0}
        ]

    def generate_preview_html(self, content_data: Dict) -> str:
        """Generate HTML preview of LinkedIn post."""
        text = content_data.get("text", "")

        return f'''
        <div class="linkedin-preview border rounded-lg p-6 bg-white shadow-sm">
            <div class="flex items-start gap-3">
                <div class="w-12 h-12 rounded bg-blue-700 flex items-center justify-center text-white font-bold">
                    FA
                </div>
                <div class="flex-1">
                    <div class="font-bold">FinAgent</div>
                    <div class="text-sm text-gray-500">Finance Education Platform</div>
                    <div class="mt-4 whitespace-pre-wrap">{text}</div>
                    <div class="mt-4 text-xs text-gray-400">
                        {len(text.split())} words · {len(text)} characters
                    </div>
                </div>
            </div>
        </div>
        '''

    def _parse_json(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        import json
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
```

---

## Plugin Registry

```python
# plugins/registry.py

from typing import Dict, List, Optional
from plugins.base import PlatformPlugin
from plugins.twitter_plugin import TwitterPlugin
from plugins.linkedin_plugin import LinkedInPlugin
from plugins.newsletter_plugin import NewsletterPlugin

class PluginRegistry:
    """Central registry for managing platform plugins."""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self._plugins: Dict[str, PlatformPlugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Discover and load all available plugins."""
        # Hardcoded for now, but could use dynamic discovery
        plugins = [
            TwitterPlugin(self.llm_client),
            LinkedInPlugin(self.llm_client),
            NewsletterPlugin(self.llm_client)
        ]

        for plugin in plugins:
            self.register_plugin(plugin)

    def register_plugin(self, plugin: PlatformPlugin):
        """Register a new plugin."""
        self._plugins[plugin.platform_name] = plugin

    def get_plugin(self, platform_name: str) -> Optional[PlatformPlugin]:
        """Get a specific plugin by name."""
        return self._plugins.get(platform_name)

    def list_plugins(self) -> List[Dict]:
        """List all registered plugins."""
        return [
            {
                "platform_name": plugin.platform_name,
                "display_name": plugin.display_name,
                "enabled": plugin.enabled,
                "requires_auth": plugin.requires_auth,
                "supported_formats": [
                    f.dict() for f in plugin.supported_formats
                ]
            }
            for plugin in self._plugins.values()
        ]

    def get_enabled_plugins(self) -> List[PlatformPlugin]:
        """Get all enabled plugins."""
        return [p for p in self._plugins.values() if p.enabled]

    def generate_content_all_platforms(
        self,
        raw_output: str,
        event_type: str,
        metadata: Dict
    ) -> Dict[str, Dict]:
        """Generate content for all enabled platforms."""
        results = {}

        for plugin in self.get_enabled_plugins():
            try:
                content = plugin.generate_content(raw_output, event_type, metadata)
                is_valid, errors = plugin.validate_content(content)

                results[plugin.platform_name] = {
                    "content": content,
                    "valid": is_valid,
                    "errors": errors
                }
            except Exception as e:
                results[plugin.platform_name] = {
                    "content": None,
                    "valid": False,
                    "errors": [str(e)]
                }

        return results
```

---

## Database Schema (Updated)

```python
# database/models.py

class GeneratedContent(Base):
    """Platform-agnostic generated content."""

    __tablename__ = "generated_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id"))

    # Plugin information
    platform_name = Column(String(50), nullable=False)  # From plugin.platform_name
    content_format = Column(String(50), nullable=False)  # "thread", "single_post", etc.

    # Content data (flexible JSONB for any platform)
    content_data = Column(JSONB, nullable=False)

    # Validation
    validation_passed = Column(Boolean, default=False)
    validation_errors = Column(JSONB)

    # Metadata
    word_count = Column(Integer)
    char_count = Column(Integer)
    metadata = Column(JSONB)  # Platform-specific metadata

    # Status
    status = Column(String(20), default="generated")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    output = relationship("Output", back_populates="generated_contents")


class PlatformCredentials(Base):
    """Store platform authentication credentials."""

    __tablename__ = "platform_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_name = Column(String(50), nullable=False, unique=True)
    credentials = Column(JSONB, nullable=False)  # Encrypted credentials
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## API Endpoints (Plugin-Aware)

```python
# api/routes/content_generation.py

from plugins.registry import PluginRegistry

# Initialize registry
plugin_registry = PluginRegistry(llm_client)

@router.get("/plugins")
async def list_plugins():
    """List all available platform plugins."""
    return {
        "plugins": plugin_registry.list_plugins()
    }

@router.post("/generate/{output_id}")
async def generate_content(
    output_id: str,
    platforms: Optional[List[str]] = None  # Specific platforms, or all if None
):
    """Generate content for specified platforms."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        output = repo.outputs.get_by_id(UUID(output_id))

        if not output:
            raise HTTPException(404, "Output not found")

        # Generate for all platforms or specified ones
        if not platforms:
            results = plugin_registry.generate_content_all_platforms(
                raw_output=output.llm_output,
                event_type=output.event_type,
                metadata={
                    "source": output.event.source if output.event else None,
                    "title": output.event.title if output.event else None
                }
            )
        else:
            results = {}
            for platform_name in platforms:
                plugin = plugin_registry.get_plugin(platform_name)
                if not plugin:
                    continue

                content = plugin.generate_content(
                    output.llm_output,
                    output.event_type,
                    {"source": output.event.source if output.event else None}
                )
                is_valid, errors = plugin.validate_content(content)

                results[platform_name] = {
                    "content": content,
                    "valid": is_valid,
                    "errors": errors
                }

        # Save to database
        for platform_name, result in results.items():
            if result["valid"]:
                generated = GeneratedContent(
                    output_id=output.id,
                    platform_name=platform_name,
                    content_format=result["content"]["format"],
                    content_data=result["content"],
                    validation_passed=True,
                    validation_errors=[],
                    word_count=result["content"].get("word_count"),
                    char_count=result["content"].get("char_count")
                )
                db.add(generated)

        db.commit()

        return {"results": results}

@router.post("/publish/{generated_content_id}")
async def publish_content(generated_content_id: str):
    """Publish generated content to platform."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        content = repo.generated_content.get_by_id(UUID(generated_content_id))

        if not content:
            raise HTTPException(404, "Content not found")

        # Get plugin
        plugin = plugin_registry.get_plugin(content.platform_name)
        if not plugin:
            raise HTTPException(404, f"Plugin '{content.platform_name}' not found")

        # Get credentials
        credentials = repo.platform_credentials.get_by_platform(content.platform_name)
        if not credentials:
            raise HTTPException(401, f"No credentials for '{content.platform_name}'")

        # Publish
        result = plugin.publish(
            content_data=content.content_data,
            credentials=credentials.credentials
        )

        if result["success"]:
            # Save published content
            published = PublishedContent(
                content_queue_id=content.id,
                platform=content.platform_name,
                platform_post_id=result["platform_id"],
                platform_url=result["platform_url"],
                content_text=str(content.content_data),
                published_at=datetime.utcnow()
            )
            db.add(published)
            db.commit()

        return result
```

---

## Benefits of Plugin Architecture

### 1. Extensibility
```python
# Add Instagram plugin without touching core code
class InstagramPlugin(PlatformPlugin):
    @property
    def platform_name(self) -> str:
        return "instagram"

    # Implement interface methods...

# Register
plugin_registry.register_plugin(InstagramPlugin(llm_client))
```

### 2. Platform Independence
- Each plugin defines its own rules
- No hardcoded platform logic in core
- Easy to add/remove platforms

### 3. Content Format Flexibility
```python
# Twitter supports threads AND single tweets
supported_formats = [
    ContentFormat(name="thread", max_length=280, max_items=5),
    ContentFormat(name="single_tweet", max_length=280, max_items=1)
]

# LinkedIn supports posts AND articles
supported_formats = [
    ContentFormat(name="single_post", max_length=3000),
    ContentFormat(name="article", max_length=125000, supports_html=True)
]
```

### 4. Easy Testing
```python
# Mock plugin for testing
class MockPlugin(PlatformPlugin):
    def publish(self, content_data, credentials):
        return {"success": True, "platform_id": "mock123"}

# Test without hitting real APIs
```

### 5. Feature Flags
```python
# Disable plugin without removing code
class TwitterPlugin(PlatformPlugin):
    @property
    def enabled(self) -> bool:
        return config.TWITTER_ENABLED  # Environment variable
```

---

## Future Plugins (Easy to Add)

### Instagram Plugin
- Supports: single_post, carousel, story
- Max length: 2200 chars
- Requires: image/video

### YouTube Plugin
- Supports: video, short
- Max length: Unlimited (description)
- Requires: video file

### Telegram Plugin
- Supports: message, photo_message
- Max length: 4096 chars
- Supports: Markdown

### WhatsApp Business Plugin
- Supports: message, broadcast
- Max length: 4096 chars
- Requires: verified business account

---

## Next Steps

1. **Implement Base Plugin Class** - Create `plugins/base.py`
2. **Implement Twitter Plugin** - Create `plugins/twitter_plugin.py`
3. **Implement LinkedIn Plugin** - Create `plugins/linkedin_plugin.py`
4. **Implement Newsletter Plugin** - Create `plugins/newsletter_plugin.py`
5. **Create Plugin Registry** - Central manager for all plugins
6. **Update Database Schema** - Add `platform_name` to `generated_content`
7. **Update API Endpoints** - Make plugin-aware
8. **Update Frontend** - Dynamic platform list from plugins
9. **Test with Real Data** - Generate and publish to all platforms

---

**End of Plugin Architecture**

*Created: January 21, 2026*
*Version: 1.0*
