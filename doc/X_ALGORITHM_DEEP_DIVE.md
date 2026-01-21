# X (Twitter) Algorithm Deep Dive Documentation

> Comprehensive technical documentation of X's recommendation, ranking, and content moderation systems.
> Created for FinAgent to inform content strategy and system design.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Recommendation Pipeline](#3-recommendation-pipeline)
4. [Candidate Generation Systems](#4-candidate-generation-systems)
5. [Ranking Systems](#5-ranking-systems)
6. [Embedding Systems](#6-embedding-systems)
7. [Community Notes Algorithm](#7-community-notes-algorithm)
8. [Trust & Safety Systems](#8-trust--safety-systems)
9. [Engagement Scoring](#9-engagement-scoring)
10. [Technical Infrastructure](#10-technical-infrastructure)
11. [Implications for FinAgent](#11-implications-for-finagent)
12. [References](#12-references)

---

## 1. Executive Summary

X (formerly Twitter) operates one of the world's largest real-time content recommendation systems, processing **500 million tweets daily** and serving **5 billion timeline requests per day**. The system completes full recommendation cycles in under **1.5 seconds**.

### Core Philosophy

X's algorithm balances three competing objectives:
1. **Relevance** - Show content users want to engage with
2. **Diversity** - Prevent filter bubbles and ensure variety
3. **Safety** - Filter harmful content while preserving reach

### Key Innovations

| Innovation | Description |
|------------|-------------|
| **Bridging Algorithm** | Community Notes uses matrix factorization to find consensus across political divides |
| **SimClusters** | 145,000 virtual communities enable sparse, interpretable embeddings |
| **MaskNet** | 48M parameter neural network with instance-guided masking |
| **GraphJet** | Real-time bipartite graph processing at 1M edges/second |

---

## 2. System Architecture Overview

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           X RECOMMENDATION SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   500M      │    │  Candidate  │    │   Light     │    │   Heavy     │  │
│  │   Tweets    │───▶│ Generation  │───▶│   Ranker    │───▶│   Ranker    │  │
│  │   Daily     │    │  (~1,500)   │    │  (~400)     │    │  (Final)    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                            │                                      │         │
│                            ▼                                      ▼         │
│                    ┌───────────────┐                    ┌─────────────────┐ │
│                    │ • Earlybird   │                    │ • Home Mixer    │ │
│                    │ • SimClusters │                    │ • Ads Blending  │ │
│                    │ • GraphJet    │                    │ • Filters       │ │
│                    │ • CR-Mixer    │                    │ • Delivery      │ │
│                    └───────────────┘                    └─────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Repository Structure

```
twitter/the-algorithm/
├── home-mixer/          # Timeline assembly service
├── cr-mixer/            # Candidate retrieval mixing
├── product-mixer/       # Component framework
├── pushservice/         # Notification recommendations
├── src/
│   ├── java/
│   │   └── twitter/
│   │       └── search/  # Earlybird search index
│   └── scala/
│       └── twitter/
│           ├── simclusters_v2/    # Community detection
│           ├── interaction_graph/ # Real Graph
│           └── graph/batch/job/tweepcred/  # Reputation
├── navi/                # ML model serving (Rust)
├── visibilitylib/       # Content moderation
└── trust_and_safety_models/  # Safety ML models
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Languages | Scala (66%), Java (20%), Python, Rust |
| ML Frameworks | TensorFlow, PyTorch, ONNX |
| Data Processing | Scalding, Heron, BigQuery, Dataflow |
| Storage | Manhattan, Nighthawk, Kafka |
| Serving | Finagle RPC, Navi (Rust) |
| Search | Lucene (Earlybird) |

---

## 3. Recommendation Pipeline

### 3.1 Timeline Composition

The "For You" timeline consists of:

| Source | Percentage | Description |
|--------|------------|-------------|
| **In-Network** | ~50% | Tweets from accounts you follow |
| **Out-of-Network (Embeddings)** | ~35% | Similar content via SimClusters/TwHIN |
| **Out-of-Network (Graph)** | ~15% | Social graph traversals via GraphJet |

### 3.2 Pipeline Stages

#### Stage 1: Candidate Generation (~1,500 tweets)

Multiple sources contribute candidates in parallel:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CANDIDATE SOURCES                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Earlybird  │  │ SimClusters │  │   GraphJet  │             │
│  │   Search    │  │     ANN     │  │    SALSA    │             │
│  │   (~50%)    │  │             │  │   (~15%)    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    UTEG     │  │     FRS     │  │   CR-Mixer  │             │
│  │  (Graph)    │  │  (Follow)   │  │  (Blender)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Stage 2: Light Ranking (~400 tweets)

- **Model**: Logistic Regression
- **Purpose**: Quick filtering of candidates
- **Key Signal**: Real Graph score (user-user engagement likelihood)
- **Separate Models**: In-network vs Out-of-network

#### Stage 3: Heavy Ranking (Final)

- **Model**: MaskNet (48M parameters)
- **Features**: ~6,000 features per tweet
- **Outputs**: 10 engagement probability predictions
- **Latency**: Sub-second inference

#### Stage 4: Filtering & Heuristics

- Author diversity (limit tweets from same author)
- Content balance (in-network vs out-of-network)
- Feedback fatigue management
- Visibility filtering (safety)
- Deduplication

#### Stage 5: Mixing & Delivery

- Blend with ads, who-to-follow modules
- Apply conversation threading
- Add social context
- Generate client instructions

---

## 4. Candidate Generation Systems

### 4.1 Earlybird (Real-Time Search)

Earlybird is Twitter's real-time search engine built on Apache Lucene.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      EARLYBIRD CLUSTERS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │   Realtime      │  │   Protected     │  │    Archive     │  │
│  │   Cluster       │  │   Cluster       │  │    Cluster     │  │
│  │   (~7 days)     │  │   (~7 days)     │  │  (All tweets)  │  │
│  └─────────────────┘  └─────────────────┘  └────────────────┘  │
│                                                                 │
│  Each cluster: Sharded + Replicated                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Features

| Feature | Description |
|---------|-------------|
| **Indexing Latency** | 1 second (reduced from 15s in 2020) |
| **Concurrency** | Single-writer, multiple-reader |
| **Index Format** | 32-bit postings (24-bit doc ID + 8-bit position) |
| **Document IDs** | Allocated high-to-low for recency ordering |

#### Data Pipeline

```
Kafka (tweets) → Ingesters → Intermediate Kafka → Earlybird Index
                    ↑
            Feature Update Service (engagement metrics)
```

### 4.2 SimClusters (Community Detection)

SimClusters discovers overlapping communities to create sparse, interpretable embeddings.

#### Algorithm: Metropolis-Hastings Community Detection

```python
# Conceptual Algorithm
1. Build Producer-Producer similarity graph
   - Nodes: Users who are followed (Producers)
   - Edges: Cosine similarity of their followers

2. Run Metropolis-Hastings sampling
   - Parameter k = number of communities to detect
   - Output: Assignment of producers to communities

3. Generate KnownFor dataset
   - Maps: clusterId → producerUserId
   - Covers: Top 20M producers
   - Output: Sparse (each producer → 1 community max)
```

#### Embedding Types

| Embedding | Computation | Update Frequency |
|-----------|-------------|------------------|
| **KnownFor** | MH clustering on follow graph | Batch (offline) |
| **InterestedIn** | Follow matrix × KnownFor matrix | Batch (offline) |
| **Producer** | Cosine sim with community InterestedIn | Batch (offline) |
| **Tweet** | Sum of favoriters' InterestedIn vectors | Real-time (streaming) |
| **Topic** | Weighted favorites on topic-annotated tweets | Batch (offline) |

#### Scale

- **Communities**: 145,000
- **Users Covered**: 1 billion potential
- **Dimensions**: 100k (sparse)
- **Top 400 tweets** stored per SimCluster
- **Top 100 SimClusters** stored per tweet

### 4.3 GraphJet (Real-Time Graph Processing)

GraphJet maintains a real-time bipartite interaction graph for recommendations.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GRAPHJET                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bipartite Graph:                                               │
│  ┌─────────┐                           ┌─────────┐             │
│  │  Users  │◀────── interactions ─────▶│ Tweets  │             │
│  │ (Left)  │                           │ (Right) │             │
│  └─────────┘                           └─────────┘             │
│                                                                 │
│  Storage: Edge pools with power-law allocation                  │
│  - Pool i has size 2^i                                         │
│  - New pool created when full: size 2^(i+1)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### SALSA Algorithm (Personalized Random Walk)

```python
# SALSA for User Recommendations
def salsa_recommendations(query_user, graph, alpha=0.15):
    """
    Personalized SALSA random walk

    Parameters:
    - query_user: Starting user node
    - graph: Bipartite user-tweet graph
    - alpha: Reset probability (personalization)

    Returns:
    - Ranked list of recommended tweets
    """

    # Random walk with reset
    for iteration in range(num_iterations):
        # Left → Right: User → Tweet
        current_tweet = random_neighbor(current_user, graph)

        # Right → Left: Tweet → User
        current_user = random_neighbor(current_tweet, graph)

        # Reset with probability alpha
        if random() < alpha:
            current_user = query_user

    return ranked_tweets_by_visit_count
```

#### Performance

| Metric | Value |
|--------|-------|
| **Edge Ingestion** | 1 million edges/second |
| **Recommendations** | 500/second |
| **Memory** | <30 GB for O(10⁹) edges |
| **Sliding Window** | Configurable time window |

### 4.4 CR-Mixer (Candidate Retrieval Mixer)

CR-Mixer is a lightweight coordinator for out-of-network recommendations.

#### Pipeline

```
1. Source Signal Extraction
   └── Fetch from UserProfileService, RealGraph

2. Candidate Generation
   └── Call external services (SimClusters ANN, etc.)

3. Filtering
   └── Deduplication, pre-ranking filters

4. Light Ranking
   └── Score and select top candidates
```

---

## 5. Ranking Systems

### 5.1 Light Ranker

Simple logistic regression for quick candidate filtering.

#### Characteristics

| Property | Value |
|----------|-------|
| **Model Type** | Logistic Regression |
| **Separate Models** | In-network, Out-of-network |
| **Features** | ~10 highly informative |
| **Output** | ~400 candidates |
| **Training** | "Several years ago" (per Twitter docs) |

#### Key Features

- Aggregate user interaction counts
- Likes and replies (heavily weighted)
- Social graph signals
- Real Graph scores

### 5.2 Heavy Ranker (MaskNet)

The core neural network for final tweet ranking.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MASKNET ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input Features (~6,000)                                        │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PARALLEL MASKBLOCKS (x4)                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │MaskBlock1│ │MaskBlock2│ │MaskBlock3│ │MaskBlock4│   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              BOTTLENECK MLP                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           MULTI-TASK OUTPUT HEADS                        │   │
│  │  P(Like) P(RT) P(Reply) P(Click) P(Report) P(Block)...  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### MaskBlock Formula

```
Output = x₀ ○ U·g(V^T·x₀^T + β)

Where:
- ○ = Hadamard (element-wise) product
- U, V = Learned factorization matrices
- g = Non-linear activation
- β = Bias term
- LayerNorm applied to output
```

#### Model Specifications

| Property | Value |
|----------|-------|
| **Parameters** | ~48 million |
| **Architecture** | Parallel MaskNet (similar to MMoE) |
| **Input Features** | ~6,000 |
| **Output Predictions** | 10 probabilities |
| **Normalization** | LayerNorm |

#### Output Predictions

The model predicts probabilities for:

1. **P(Favorite)** - User will like the tweet
2. **P(Retweet)** - User will retweet
3. **P(Reply)** - User will reply
4. **P(Profile Click)** - User will click author profile
5. **P(URL Click)** - User will click embedded link
6. **P(Video Watch)** - User will watch video (50%+)
7. **P(Detail Expand)** - User will expand tweet details
8. **P(Report)** - User will report tweet
9. **P(Block)** - User will block author
10. **P(Mute)** - User will mute author

### 5.3 Real Graph (User-User Prediction)

Predicts likelihood of engagement between user pairs.

#### Model

| Property | Value |
|----------|-------|
| **Algorithm** | XGBoost (Gradient Boosting) |
| **Training** | BigQuery ML |
| **Features** | ~10 highly informative |
| **Output** | Interaction probability |

#### Features

```python
# Real Graph Features (from interaction_graph)
features = {
    # Public Engagements
    'favorites_count': int,      # Likes given
    'retweets_count': int,       # Retweets given
    'follows_count': int,        # Follow actions
    'replies_count': int,        # Replies sent

    # Private Engagements
    'profile_views': int,        # Profile visits
    'tweet_clicks': int,         # Click interactions
    'address_book': bool,        # In contacts

    # Aggregates
    'interaction_recency': float,
    'interaction_frequency': float,
}
```

#### Training Process

```python
# Conceptual Training Pipeline
1. Select candidate edges (active in time period T)
2. Join with labels (interactions in T+1 day)
3. Label: 1 = interaction occurred, 0 = no interaction
4. Train XGBoost on features
5. Score all user pairs
6. Output: Decay-weighted interaction likelihood
```

### 5.4 TweepCred (Reputation Scoring)

PageRank-based reputation score for users.

#### Algorithm

```python
# TweepCred Calculation
def calculate_tweepcred(raw_pagerank, followers, following):
    """
    Convert raw PageRank to TweepCred score (0-100)
    """
    # Step 1: Scale PageRank to 0-100
    scaled = 130 + 5.21 * math.log(raw_pagerank)
    scaled = max(0, min(100, scaled))

    # Step 2: Penalize low follower/following ratio
    if followers > 0:
        ratio = following / followers
        if ratio > 1:
            # Penalty for following more than followers
            penalty_factor = 1 + (ratio - 1) * penalty_coefficient
            scaled = scaled / penalty_factor

    return int(scaled)
```

#### Impact on Visibility

| TweepCred Score | Effect |
|-----------------|--------|
| **< 65** | Max 3 tweets considered by algorithm |
| **≥ 65** | No limit on tweets considered |

#### Factors

- Account age
- Follower count and quality
- Engagement patterns
- Follower/following ratio
- Device usage patterns

---

## 6. Embedding Systems

### 6.1 TwHIN (Heterogeneous Information Network)

TwHIN learns embeddings across Twitter's knowledge graph.

#### Network Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    TwHIN KNOWLEDGE GRAPH                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Entity Types:                                                  │
│  ┌────────┐  ┌────────┐  ┌────────────┐  ┌────────┐           │
│  │  User  │  │ Tweet  │  │ Advertiser │  │   Ad   │           │
│  └────────┘  └────────┘  └────────────┘  └────────┘           │
│                                                                 │
│  Relationship Types:                                            │
│  • Follows (261M edges)                                        │
│  • Authors                                                      │
│  • Favorites (283M edges)                                      │
│  • Replies                                                      │
│  • Retweets                                                     │
│  • Promotes                                                     │
│  • Clicks                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Training

| Property | Value |
|----------|-------|
| **Method** | TransE-style knowledge graph embeddings |
| **Scale** | 10⁹ nodes, 10¹¹ edges |
| **Hardware** | 16x A100 GPUs, 1.4TB RAM |
| **Embedding Dim** | 128 (compressed for serving) |

#### Applications

- Personalized ads ranking (+2.38 RCE, -10.3% cost-per-conversion)
- Account follow recommendations
- Offensive content detection
- Search ranking

### 6.2 Navi (ML Model Serving)

High-performance model serving written in Rust.

#### Features

| Feature | Description |
|---------|-------------|
| **Language** | Rust (performance + safety) |
| **API** | gRPC (TF Serving compatible) |
| **Runtimes** | TensorFlow, ONNX, PyTorch (experimental) |
| **Batching** | Automatic request batching |
| **Concurrency** | High-throughput inference |

### 6.3 Representation Manager

Centralized service for embedding retrieval.

```
┌─────────────────────────────────────────────────────────────────┐
│                 REPRESENTATION MANAGER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Embeddings Served:                                             │
│  • SimClusters (user, tweet, topic)                            │
│  • TwHIN (user, tweet, advertiser)                             │
│                                                                 │
│  Operations:                                                    │
│  • Retrieve by entity ID                                       │
│  • Compute similarity scores                                   │
│  • Batch lookups                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Community Notes Algorithm

Community Notes (formerly Birdwatch) uses a **bridging algorithm** to identify helpful annotations across political divides.

### 7.1 Core Concept: Bridging

The algorithm factors out political bias to find **genuine consensus**.

```
Traditional Voting:
  Left users upvote left content → Left content wins

Bridging Algorithm:
  Factor out political bias → Find content helpful to BOTH sides
```

### 7.2 Matrix Factorization Model

#### The Note-Rater Matrix

```
                    Notes
              n₁   n₂   n₃   n₄
         u₁ [ 1    0    -    1  ]
Raters   u₂ [ -    1    0    -  ]
         u₃ [ 0    1    1    -  ]
         u₄ [ 1    -    0    1  ]

Where:
  1 = Helpful rating
  0 = Not helpful rating
  - = No rating (sparse)
```

#### Prediction Formula

```
r̂ᵤₙ = μ + iᵤ + iₙ + fᵤ · fₙ

Where:
  μ   = Global intercept (baseline)
  iᵤ  = User intercept (rater leniency/strictness)
  iₙ  = NOTE INTERCEPT = HELPFULNESS SCORE ★
  fᵤ  = User factor (political leaning, 1D)
  fₙ  = Note factor (political leaning, 1D)
```

#### Loss Function

```
L = Σ(rᵤₙ - r̂ᵤₙ)² + λᵢ(iᵤ² + iₙ² + μ²) + λf(||fᵤ||² + ||fₙ||²)

Parameters:
  λᵢ = 0.15  (intercept regularization - HIGH)
  λf = 0.03  (factor regularization - LOW)
```

#### Why Asymmetric Regularization?

High regularization on intercepts forces the model to:
1. **First** explain variance through polarity factors (political alignment)
2. **Then** fit intercepts only for what remains (genuine helpfulness)

Result: Notes with high `iₙ` are helpful **regardless of political viewpoint**.

### 7.3 Rating Mapping

| User Response | Numeric Value |
|---------------|---------------|
| Yes | 1.0 |
| Somewhat | 0.5 |
| No | 0.0 |

### 7.4 Status Thresholds

#### Helpful Status

```python
def is_helpful(note):
    return (
        note.intercept >= 0.40 and
        abs(note.factor) < 0.50 and
        passes_agreement_safeguards(note) and
        note.baseline_intercept >= 0.37
    )
```

#### Not Helpful Status

```python
def is_not_helpful(note):
    return (
        note.intercept < -0.05 - 0.8 * abs(note.factor) or
        note.upper_confidence_bound < -0.04 or
        mean_helpfulness_ratio(note) <= 0.4
    )
```

#### Default Status

- "Needs More Ratings" until ≥5 total ratings

### 7.5 Agreement Safeguards

To prevent gaming, notes must have broad support:

```python
# Net Helpful Minimums
def passes_safeguards(note):
    # Option 1: Strong support from both sides
    if (net_helpful_from_positive_factor >= 10 and
        net_helpful_from_negative_factor >= 10):
        return True

    # Option 2: Moderate support with good ratio
    if (net_helpful_from_positive_factor >= 4 and
        net_helpful_from_negative_factor >= 4 and
        net_helpful_ratio_positive >= 0.05 and
        net_helpful_ratio_negative >= 0.05):
        return True

    return False
```

### 7.6 Multi-Model Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 COMMUNITY NOTES MODELS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Core Model:                                                    │
│  └── Ratings from established regions                          │
│  └── Excludes topic-assigned notes                             │
│                                                                 │
│  Expansion/ExpansionPlus:                                       │
│  └── All ratings across regions                                │
│                                                                 │
│  Group Models:                                                  │
│  └── Separate MF per language/region                           │
│  └── Promotes from Needs More Ratings → Helpful                │
│  └── When core intercept ∈ [0.3, 0.4]                         │
│                                                                 │
│  Topic Models:                                                  │
│  └── Topic-specific via seed-term assignment                   │
│  └── Logistic regression classification                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.7 Processing Pipeline

```python
# Community Notes Pipeline
def process_notes():
    # 1. Pre-filter
    raters = filter(lambda r: r.rating_count >= 10, all_raters)
    notes = filter(lambda n: n.rating_count >= 5, all_notes)

    # 2. First MF fit
    model = MatrixFactorization()
    model.fit(notes, raters)

    # 3. Assign intermediate labels
    for note in notes:
        note.provisional_status = get_status(note.intercept, note.factor)

    # 4. Compute rater helpfulness
    for rater in raters:
        rater.helpfulness_score = compute_helpfulness(rater, notes)

    # 5. Filter low-quality raters
    quality_raters = filter(lambda r: r.helpfulness_score >= 0.66, raters)

    # 6. Second MF fit (final)
    model.fit(notes, quality_raters)

    # 7. Assign final statuses
    for note in notes:
        note.final_status = get_status(note.intercept, note.factor)

    # 8. Apply stability rules for older notes
    apply_status_stability(notes)
```

### 7.8 Retraining

- **Frequency**: Every hour
- **Convergence Check**: Loss threshold of 0.09
- **Re-initialization**: If loss too high, retry with new random init

---

## 8. Trust & Safety Systems

### 8.1 Visibility Filtering

Centralized rule engine for content moderation.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 VISIBILITY FILTERING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input:                                                         │
│  • SafetyLevel (context: Timeline, Profile, Search)            │
│  • Features (labels, metadata, relationships)                  │
│                                                                 │
│  Processing:                                                    │
│  • Evaluate Conditions against Features                        │
│  • Apply Rules sequentially per SafetyLevel                    │
│  • Default action: Allow                                       │
│                                                                 │
│  Output Actions:                                                │
│  • Hard filtering (Drop)                                       │
│  • Soft filtering (Labels, Interstitials)                      │
│  • Ranking signals (downrank/uprank)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Action Types

| Action | Description |
|--------|-------------|
| **Drop** | Complete removal from surface |
| **Interstitial** | Warning screen before viewing |
| **Label** | Informational label attached |
| **Downrank** | Reduced visibility in ranking |
| **Tombstone** | Placeholder indicating removed content |

### 8.2 Safety Labels

Labels applied to entities (tweets, users, media, spaces).

```python
# Safety Label Structure
class SafetyLabel:
    label_type: SafetyLabelType  # Type of violation
    source: str                   # Who applied (ML, human, etc.)
    created_at: datetime
    expires_at: Optional[datetime]
```

### 8.3 Shadowbanning

Acknowledged moderation under "freedom of speech, not freedom of reach."

#### Triggers

- Bot-like behavior patterns
- Mass following/unfollowing
- Excessive automation
- Policy violations
- Suspicious authentication

#### Duration

| Offense | Duration |
|---------|----------|
| First | 48-72 hours |
| Repeat | 7-14 days |
| Mass unfollow | 3 months |

### 8.4 ML Safety Models

| Model | Purpose |
|-------|---------|
| **NSFW Detection** | Adult content classification |
| **Abuse Detection** | Harassment identification |
| **Spam Detection** | Automated/spam content |
| **Misinformation** | False information flagging |

---

## 9. Engagement Scoring

### 9.1 Heavy Ranker Scoring Formula

```python
# Engagement Score Calculation
score = (
    0.5  * P(Favorite) +
    1.0  * P(Retweet) +
    13.5 * P(Reply) +
    0.15 * P(ProfileClick) +
    11.0 * P(ConversationDwell2Min) +
    75.0 * P(ReplyToReplyEngagement) -  # Author replies to reply
    74.0 * P(NegativeAction) -          # Block/Mute/Hide
    369.0 * P(Report)                    # Report button
)
```

### 9.2 Engagement Multipliers

| Engagement Type | Multiplier |
|-----------------|------------|
| **Reply-to-reply (author engagement)** | **75×** |
| **Direct reply** | 13.5-27× |
| **Conversation dwell (2+ min)** | 11× |
| **Quote tweet** | >1× (higher than RT) |
| **Retweet** | 1× |
| **Like/Favorite** | 0.5× |
| **Video 50%+ watch** | 0.005× |

### 9.3 Negative Signal Penalties

| Signal | Penalty |
|--------|---------|
| **Report** | **-369×** |
| **Block/Mute/Hide** | **-74×** |
| Unfollow | Potential 3-month shadowban |

### 9.4 Content Type Boosts

| Content Type | Effect |
|--------------|--------|
| **Native video** | 10× engagement vs text |
| **Images/GIFs** | Boost |
| **Text-only** | Baseline |
| **External links** | **Severe penalty** (esp. non-Premium) |

### 9.5 Premium (Blue) Advantages

| Feature | Boost |
|---------|-------|
| In-network visibility | **4×** |
| Out-of-network visibility | **2×** |
| Reply priority | Top of threads |
| Link posts | Actually visible |

### 9.6 Timing Factors

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIMING CRITICAL                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  First 30 Minutes:                                              │
│  • Most critical engagement window                             │
│  • Early engagement → signals quality → wider distribution     │
│  • Dormant tweets → deprioritized                              │
│                                                                 │
│  Momentum Effect:                                               │
│  • High early engagement creates flywheel                      │
│  • Low early engagement → algorithm "gives up"                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Technical Infrastructure

### 10.1 Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Lambda Architecture:                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Batch Layer                                             │   │
│  │  • Scalding (Hadoop MapReduce)                          │   │
│  │  • BigQuery                                              │   │
│  │  • Accurate views of historical data                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Speed Layer                                             │   │
│  │  • Heron (Stream processing)                            │   │
│  │  • Kafka                                                 │   │
│  │  • Real-time views of recent data                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Serving Layer                                           │   │
│  │  • Manhattan (Key-value store)                          │   │
│  │  • Nighthawk (Distributed cache)                        │   │
│  │  • Merged batch + real-time views                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 User Signal Service (USS)

Centralized platform for user behavior data.

#### Signals Collected

| Signal Type | Examples |
|-------------|----------|
| **Explicit** | Favorites, retweets, replies, follows |
| **Implicit** | Tweet clicks, video views, profile visits, dwell time |

#### Processing

- Gathers from various underlying datasets
- Normalizes into uniform formats
- Serves for candidate retrieval and ranking features

### 10.3 Feature Store

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEATURE STORE                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Batch Features:                                                │
│  • Pre-computed in BigQuery/Scalding                           │
│  • Updated periodically                                        │
│  • Historical aggregates                                       │
│                                                                 │
│  Real-time Features:                                            │
│  • Computed via Heron streaming                                │
│  • Stored in Nighthawk cache                                   │
│  • Recent engagement signals                                   │
│                                                                 │
│  Graph Features:                                                │
│  • Interaction counts between user pairs                       │
│  • Real Graph scores                                           │
│  • Social proof signals                                        │
│                                                                 │
│  Embedding Features:                                            │
│  • SimClusters vectors (sparse, 145k dim)                     │
│  • TwHIN vectors (dense, 128 dim)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.4 Push Notification System

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUSHSERVICE PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Target Construction & Eligibility                          │
│     └── Is user eligible for notifications?                    │
│                                                                 │
│  2. Candidate Retrieval                                        │
│     └── Query candidate sources                                │
│                                                                 │
│  3. Hydration                                                  │
│     └── Enrich with downstream service data                    │
│                                                                 │
│  4. Light Filtering                                            │
│     └── Quick RPC-based filters                                │
│                                                                 │
│  5. Light Ranking                                              │
│     └── Score candidates                                       │
│                                                                 │
│  6. Heavy Ranking                                              │
│     └── Multi-task learning: P(open), P(engage)               │
│                                                                 │
│  7. Heavy Filtering                                            │
│     └── Take top candidates through intensive filters          │
│                                                                 │
│  8. Delivery                                                   │
│     └── Route to notification services                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Implications for FinAgent

### 11.1 Content Strategy Recommendations

Based on the algorithm analysis, FinAgent should optimize for:

#### High-Value Engagement Patterns

| Strategy | Reason | Algorithm Basis |
|----------|--------|-----------------|
| **Reply to comments** | 75× multiplier for author engagement | Heavy Ranker weights |
| **Encourage replies** | 13.5-27× multiplier | Heavy Ranker weights |
| **Use native media** | 10× engagement boost | Content type signals |
| **Avoid external links** | Severe penalty | Link demotion |
| **Post timing matters** | First 30 min critical | Momentum algorithm |

#### Content Philosophy Alignment

| FinAgent Principle | X Algorithm Benefit |
|--------------------|---------------------|
| **Educational, no-advice** | High bridging score (appeals across political spectrum) |
| **Factual, calm tone** | Low report probability (-369× avoided) |
| **No sensationalism** | Avoids negative signals |
| **Accessible language** | Broader audience engagement |

### 11.2 Bridging Score Optimization

FinAgent's content naturally aligns with high Community Notes bridging scores:

```
FinAgent Content Characteristics:
├── No political bias → Low factor score (fₙ ≈ 0)
├── Factual explanations → High intercept (iₙ)
├── Educational value → Helpful across spectrum
└── No advice/predictions → Non-controversial
```

### 11.3 Reputation Building (TweepCred)

To maximize algorithmic reach:

```python
# TweepCred Optimization
goals = {
    'target_score': 65,  # Minimum for unlimited tweet consideration

    'strategies': [
        'Build follower quality over quantity',
        'Maintain healthy follower/following ratio',
        'Consistent engagement patterns',
        'Avoid bot-like behavior',
    ]
}
```

### 11.4 Content Format Recommendations

| Format | Recommendation | Reason |
|--------|----------------|--------|
| **Text** | Thread format for explanations | Engagement depth |
| **Images** | Infographics, charts | Visual boost |
| **Video** | Short explainers (<60s) | 10× engagement |
| **Links** | Minimize or use Premium | Link penalty |
| **Polls** | Engagement driver | Interaction boost |

### 11.5 Posting Schedule

```
Optimal Posting Strategy:
├── Time: Audience active hours (experiment)
├── Frequency: Consistent, not spammy
├── Engagement: Reply within first 30 min
└── Monitoring: Track early engagement signals
```

### 11.6 Anti-Patterns to Avoid

| Anti-Pattern | Risk | Algorithm Penalty |
|--------------|------|-------------------|
| Mass following/unfollowing | Shadowban | 3-month visibility loss |
| Automation abuse | Account flags | TweepCred reduction |
| Controversial advice | Reports | -369× per report |
| External link spam | Demotion | Severe visibility loss |
| Engagement bait | Low quality | Negative signals |

---

## 12. References

### Official Sources

- [GitHub: twitter/the-algorithm](https://github.com/twitter/the-algorithm)
- [GitHub: twitter/communitynotes](https://github.com/twitter/communitynotes)
- [Twitter Engineering Blog](https://blog.x.com/engineering/)
- [Community Notes Guide](https://communitynotes.twitter.com/guide/)

### Academic Papers

- [SimClusters: Community-Based Representations (KDD 2020)](https://dl.acm.org/doi/10.1145/3394486.3403370)
- [TwHIN: Embedding the Twitter HIN (KDD 2022)](https://arxiv.org/abs/2202.05387)
- [Birdwatch: Crowd Wisdom and Bridging (arXiv 2022)](https://arxiv.org/abs/2210.15723)
- [Earlybird: Real-Time Search (ICDE 2012)](https://ieeexplore.ieee.org/document/6228205)
- [GraphJet: Real-Time Recommendations (VLDB 2016)](https://dl.acm.org/doi/10.14778/3007263.3007267)

### Analysis Resources

- [awesome-twitter-algo (GitHub)](https://github.com/igorbrigadir/awesome-twitter-algo)
- [Understanding Community Notes (jonathanwarden.com)](https://jonathanwarden.com/understanding-community-notes/)
- [Twitter Algorithm Breakdown (tweetarchivist.com)](https://www.tweetarchivist.com/how-twitter-algorithm-works-2025)

---

*Document Version: 1.0*
*Created: January 2026*
*For: FinAgent Pre-MVP Research*
