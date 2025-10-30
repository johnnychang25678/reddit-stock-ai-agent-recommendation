import pytest
import random
from datetime import datetime
from unittest.mock import patch
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from stock_ai.reddit.types import RedditPost


@pytest.fixture
def filter_instance():
    """Create an AfterScrapeFilter instance."""
    return AfterScrapeFilter()


@pytest.fixture
def sample_posts():
    """Create a list of sample RedditPost objects with varying scores."""
    return [
        RedditPost(
            reddit_id=f"post_{i}",
            flair="DD",
            title=f"Test Post {i}",
            selftext=f"Content for post {i}",
            score=score,
            num_comments=10,
            upvote_ratio=0.9,
            created=datetime.now(),
            url=f"https://reddit.com/{i}"
        )
        for i, score in enumerate([100, 85, 70, 60, 50, 40, 30, 20, 10, 5])
    ]


class TestAfterScrapeFilter:
    """Test suite for AfterScrapeFilter class."""

    def test_get_quantiles_normal_data(self, filter_instance: AfterScrapeFilter):
        """Test quantile calculation with normal data."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        quantiles = filter_instance._get_quantiles(data)
        
        assert len(quantiles) == 3
        assert quantiles[0] < quantiles[1] < quantiles[2]  # Q1 < Q2 < Q3
        assert quantiles[1] == 5.5  # Median of 1-10

    def test_get_quantiles_empty_data(self, filter_instance: AfterScrapeFilter):
        """Test quantile calculation with empty data."""
        quantiles = filter_instance._get_quantiles([])
        assert quantiles == [0.0, 0.0, 0.0]

    def test_get_quantiles_single_value(self, filter_instance: AfterScrapeFilter):
        """Test quantile calculation with single value."""
        quantiles = filter_instance._get_quantiles([5])
        assert quantiles == [5, 5, 5]

    def test_get_quantiles_two_values(self, filter_instance: AfterScrapeFilter):
        """Test quantile calculation with two values."""
        data = [10, 20]
        quantiles = filter_instance._get_quantiles(data)
        assert len(quantiles) == 3
        print(quantiles)
        assert all(q == 15.0 for q in quantiles)  # All should be median

    def test_select_top_post_only(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test selection returns top post when it exists."""
        result = filter_instance._select_top_and_random_q2(sample_posts, "DD")
        
        # Should return 1-2 posts
        assert 1 <= len(result) <= 2
        # First post should be the highest scored
        assert result[0].score == 100
        assert result[0].reddit_id == "post_0"

    def test_select_top_50_percent_random(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test random selection from top 50%."""
        # Set seed for reproducibility
        random.seed(42)
        
        result = filter_instance._select_top_and_random_q2(sample_posts, "DD")
        
        # Should have 2 posts (top + random)
        assert len(result) == 2
        assert result[0].score == 100  # Top post
        
        # Second post should be from top 50% (score >= median)
        # Median of [100, 85, 70, 60, 50, 40, 30, 20, 10, 5] is 45
        assert result[1].score >= 45
        # And should not be the top post
        assert result[1].reddit_id != "post_0"

    def test_select_with_insufficient_posts(self, filter_instance: AfterScrapeFilter):
        """Test selection with fewer than 3 posts."""
        posts = [
            RedditPost(
                reddit_id="post_1",
                flair="News",
                title="Post 1",
                selftext="Content",
                score=100,
                num_comments=10,
                upvote_ratio=0.9,
                created=datetime.now(),
                url="https://reddit.com/1"
            ),
            RedditPost(
                reddit_id="post_2",
                flair="News",
                title="Post 2",
                selftext="Content",
                score=50,
                num_comments=5,
                upvote_ratio=0.8,
                created=datetime.now(),
                url="https://reddit.com/2"
            )
        ]
        
        result = filter_instance._select_top_and_random_q2(posts, "News")
        
        # Should only return top 1 (not enough for random selection)
        assert len(result) == 1
        assert result[0].score == 100

    def test_select_with_empty_list(self, filter_instance: AfterScrapeFilter):
        """Test selection with empty post list."""
        result = filter_instance._select_top_and_random_q2([], "DD")
        assert result == []

    def test_select_excludes_top_post_from_random_pool(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test that top post is excluded from random selection pool."""
        # Run multiple times to ensure top post never appears as random pick
        random.seed(123)
        
        for _ in range(10):
            result = filter_instance._select_top_and_random_q2(sample_posts, "DD")
            if len(result) == 2:
                # Second post should never be the same as first
                assert result[1].reddit_id != result[0].reddit_id

    def test_call_filters_all_flairs(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test __call__ method filters posts for all flairs."""
        posts_dict = {
            "News": sample_posts[:5],
            "DD": sample_posts[3:8],
            "YOLO": sample_posts[5:]
        }
        
        result = filter_instance(posts_dict)
        
        # Should have same flairs
        assert set(result.keys()) == {"News", "DD", "YOLO"}
        
        # Each flair should have 1-2 posts
        for flair, posts in result.items():
            assert 1 <= len(posts) <= 2
            # Top post should be highest scored in original list
            original_scores = [p.score for p in posts_dict[flair]]
            assert posts[0].score == max(original_scores)

    def test_call_with_empty_flair(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test __call__ handles empty post lists for some flairs."""
        posts_dict = {
            "News": sample_posts,
            "DD": [],
            "YOLO": sample_posts[:3]
        }
        
        result = filter_instance(posts_dict)
        
        assert result["News"] != []
        assert result["DD"] == []
        assert result["YOLO"] != []

    def test_call_with_all_empty(self, filter_instance: AfterScrapeFilter):
        """Test __call__ with all empty post lists."""
        posts_dict = {
            "News": [],
            "DD": [],
            "YOLO": []
        }
        
        result = filter_instance(posts_dict)
        
        assert all(len(posts) == 0 for posts in result.values())

    def test_random_selection_distribution(self, filter_instance: AfterScrapeFilter, sample_posts):
        """Test that random selection covers multiple posts over time."""
        random.seed(999)
        
        selected_ids = set()
        
        # Run multiple times
        for _ in range(20):
            result = filter_instance._select_top_and_random_q2(sample_posts, "DD")
            if len(result) == 2:
                selected_ids.add(result[1].reddit_id)
        
        # Should have selected multiple different posts as random pick
        # (not just the same one every time)
        assert len(selected_ids) > 1

    def test_top_50_percent_boundary(self, filter_instance: AfterScrapeFilter):
        """Test selection at median boundary."""
        posts = [
            RedditPost(
                reddit_id=f"post_{i}",
                flair="DD",
                title=f"Post {i}",
                selftext="Content",
                score=score,
                num_comments=10,
                upvote_ratio=0.9,
                created=datetime.now(),
                url=f"https://reddit.com/{i}"
            )
            for i, score in enumerate([100, 60, 59, 40])  # Median = 59.5
        ]
        
        random.seed(42)
        
        # Run multiple times to check both eligible posts
        selected_scores = set()
        for _ in range(10):
            result = filter_instance._select_top_and_random_q2(posts, "DD")
            if len(result) == 2:
                selected_scores.add(result[1].score)
        
        # Only post with score 60 should be selected (score >= median 59.5)
        # Post with score 59 and 40 should not be selected
        assert 60 in selected_scores
        assert 59 not in selected_scores
        assert 40 not in selected_scores

    def test_handles_zero_scores(self, filter_instance: AfterScrapeFilter):
        """Test handling of posts with zero or very low scores."""
        posts = [
            RedditPost(
                reddit_id="post_1",
                flair="DD",
                title="Post 1",
                selftext="Content",
                score=100,
                num_comments=10,
                upvote_ratio=0.9,
                created=datetime.now(),
                url="https://reddit.com/1"
            ),
            RedditPost(
                reddit_id="post_2",
                flair="DD",
                title="Post 2",
                selftext="Content",
                score=0,  # Zero score
                num_comments=5,
                upvote_ratio=0.8,
                created=datetime.now(),
                url="https://reddit.com/2"
            ),
            RedditPost(
                reddit_id="post_3",
                flair="DD",
                title="Post 3",
                selftext="Content",
                score=50,
                num_comments=8,
                upvote_ratio=0.85,
                created=datetime.now(),
                url="https://reddit.com/3"
            )
        ]
        
        result = filter_instance._select_top_and_random_q2(posts, "DD")
        
        # Should handle zero scores gracefully
        assert len(result) >= 1
        assert result[0].score == 100

    @patch('builtins.print')
    def test_logging_output(self, mock_print, filter_instance: AfterScrapeFilter, sample_posts):
        """Test that appropriate logging messages are printed."""
        filter_instance._select_top_and_random_q2(sample_posts, "DD")
        
        # Check that print was called with flair info
        call_args = [str(call[0]) for call in mock_print.call_args_list]
        assert any("DD" in str(arg) for arg in call_args)
        assert any("Top post" in str(arg) for arg in call_args)

    def test_title_truncation_in_logging(self, filter_instance: AfterScrapeFilter):
        """Test that long titles are truncated in logs."""
        long_title = "A" * 100
        posts = [
            RedditPost(
                reddit_id="post_1",
                flair="DD",
                title=long_title,
                selftext="Content",
                score=100,
                num_comments=10,
                upvote_ratio=0.9,
                created=datetime.now(),
                url="https://reddit.com/1"
            )
        ]
        
        # Should not raise any errors with long titles
        result = filter_instance._select_top_and_random_q2(posts, "DD")
        assert len(result) == 1
