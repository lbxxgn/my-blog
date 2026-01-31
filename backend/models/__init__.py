"""
Models Package

This package provides all database models and functions for the Simple Blog application.
All functions are imported from models.py for backward compatibility.
"""

# Import all functions from models.py
from .models import *

# Export all public functions
__all__ = [
    # Database functions
    'get_db_connection',
    'get_db_context',
    'paginate_query_cursor',
    'init_db',
    'rebuild_fts_index',

    # Post functions
    'create_post',
    'update_post',
    'delete_post',
    'get_all_posts',
    'get_all_posts_cursor',
    'get_post_by_id',
    'update_post_with_tags',
    'get_post_excerpt',
    'check_post_access',
    'update_post_access',
    'verify_post_password',
    'get_posts_by_author',

    # Category functions
    'create_category',
    'get_all_categories',
    'get_category_by_id',
    'update_category',
    'delete_category',
    'get_posts_by_category',

    # Tag functions
    'create_tag',
    'get_all_tags',
    'get_tag_by_id',
    'get_popular_tags',
    'get_tag_by_name',
    'update_tag',
    'delete_tag',
    'set_post_tags',
    'get_post_tags',
    'get_posts_by_tag',

    # Comment functions
    'create_comment',
    'get_comments_by_post',
    'get_all_comments',
    'update_comment_visibility',
    'delete_comment',

    # User functions
    'create_user',
    'get_user_by_id',
    'get_user_by_username',
    'get_all_users',
    'update_user',
    'update_user_password',
    'delete_user',
    'get_user_ai_config',
    'update_user_ai_config',
    'save_ai_tag_history',
    'get_ai_tag_history',
    'get_ai_usage_stats',
    'generate_api_key',
    'validate_api_key',

    # Card functions
    'create_card',
    'get_card_by_id',
    'get_cards_by_user',
    'update_card_status',
    'update_card',
    'delete_card',
    'merge_cards_to_post',
    'ai_merge_cards_to_post',

    # Timeline functions
    'get_timeline_items',
    'create_annotation',
    'get_annotations_by_url',

    # Search functions
    'search_posts',

    # Utility functions
    'strip_html_tags',
    'truncate_text',

    # Init functions
    'init_cards_table',
    'init_api_keys_table',
    'init_card_annotations_table',
]
