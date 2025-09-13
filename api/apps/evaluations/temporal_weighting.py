"""
Temporal weighting functions for ProfileExperienceSkills.
Implements recency bias where recent experience is weighted higher.
"""

from datetime import date, timedelta
from typing import Tuple
from django.utils import timezone


def calculate_recency_weight(start_date: date, end_date: date = None) -> float:
    """
    Calculate recency weight for an experience based on how recently it ended.
    
    Args:
        start_date: When the experience started
        end_date: When the experience ended (None = current role)
        
    Returns:
        Weight between 0.1 and 1.0, where 1.0 = current or very recent
        
    Weighting Rules:
    - Current role (end_date=None): 1.0
    - Ended within 1 year: 0.9-1.0 (linear decay)
    - Ended 1-2 years ago: 0.7-0.9
    - Ended 2-3 years ago: 0.5-0.7  
    - Ended 3-5 years ago: 0.3-0.5
    - Ended 5+ years ago: 0.1-0.3
    """
    current_date = timezone.now().date()
    
    # Current role gets maximum weight
    if end_date is None:
        return 1.0
    
    # Calculate days since experience ended
    days_since_ended = (current_date - end_date).days
    
    # Convert to years for easier calculation
    years_since_ended = days_since_ended / 365.25
    
    # Apply exponential decay with floor
    if years_since_ended <= 1:
        # Linear decay from 1.0 to 0.9 over first year
        return 1.0 - (years_since_ended * 0.1)
    elif years_since_ended <= 2:
        # Decay from 0.9 to 0.7
        return 0.9 - ((years_since_ended - 1) * 0.2)
    elif years_since_ended <= 3:
        # Decay from 0.7 to 0.5
        return 0.7 - ((years_since_ended - 2) * 0.2)
    elif years_since_ended <= 5:
        # Decay from 0.5 to 0.3
        return 0.5 - ((years_since_ended - 3) * 0.1)
    else:
        # Floor at 0.1 for very old experience
        return max(0.1, 0.3 - ((years_since_ended - 5) * 0.04))


def calculate_duration_weight(start_date: date, end_date: date = None) -> float:
    """
    Calculate weight based on duration of experience.
    Longer experience generally indicates deeper skill development.
    
    Args:
        start_date: When the experience started
        end_date: When the experience ended (None = current role)
        
    Returns:
        Weight between 0.3 and 1.0 based on duration
        
    Duration Rules:
    - 0-6 months: 0.3-0.5 (internships, short contracts)
    - 6-12 months: 0.5-0.7 (getting established)
    - 1-2 years: 0.7-0.9 (good experience)
    - 2+ years: 0.9-1.0 (deep experience)
    """
    if end_date is None:
        end_date = timezone.now().date()
    
    # Calculate duration in months
    duration_days = (end_date - start_date).days
    duration_months = duration_days / 30.44  # Average month length
    
    if duration_months <= 6:
        # Short experience: 0.3 to 0.5
        return 0.3 + (duration_months / 6) * 0.2
    elif duration_months <= 12:
        # Medium experience: 0.5 to 0.7
        return 0.5 + ((duration_months - 6) / 6) * 0.2
    elif duration_months <= 24:
        # Good experience: 0.7 to 0.9
        return 0.7 + ((duration_months - 12) / 12) * 0.2
    else:
        # Deep experience: 0.9 to 1.0 (capped)
        return min(1.0, 0.9 + ((duration_months - 24) / 24) * 0.1)


def calculate_combined_temporal_weight(start_date: date, end_date: date = None) -> float:
    """
    Calculate combined temporal weight considering both recency and duration.
    
    Args:
        start_date: When the experience started
        end_date: When the experience ended (None = current role)
        
    Returns:
        Combined weight between 0.1 and 1.0
        
    Combination:
    - 70% recency weight (how recent the experience is)
    - 30% duration weight (how long the experience was)
    """
    recency_weight = calculate_recency_weight(start_date, end_date)
    duration_weight = calculate_duration_weight(start_date, end_date)
    
    # Weighted combination favoring recency
    combined_weight = (recency_weight * 0.7) + (duration_weight * 0.3)
    
    return combined_weight


def get_temporal_context_description(start_date: date, end_date: date = None) -> str:
    """
    Generate human-readable description of temporal context.
    Useful for debugging and understanding weighting decisions.
    
    Args:
        start_date: When the experience started
        end_date: When the experience ended (None = current role)
        
    Returns:
        Human-readable description of temporal factors
    """
    recency_weight = calculate_recency_weight(start_date, end_date)
    duration_weight = calculate_duration_weight(start_date, end_date)
    combined_weight = calculate_combined_temporal_weight(start_date, end_date)
    
    # Calculate human-readable values
    if end_date is None:
        recency_desc = "Current role"
        end_date_display = timezone.now().date()
    else:
        days_since = (timezone.now().date() - end_date).days
        if days_since <= 30:
            recency_desc = f"Ended {days_since} days ago"
        elif days_since <= 365:
            months_since = days_since // 30
            recency_desc = f"Ended {months_since} months ago"
        else:
            years_since = days_since // 365
            recency_desc = f"Ended {years_since} years ago"
        end_date_display = end_date
    
    duration_days = (end_date_display - start_date).days
    duration_months = duration_days // 30
    duration_desc = f"{duration_months} months duration"
    
    return f"{recency_desc}, {duration_desc} (weights: recency={recency_weight:.2f}, duration={duration_weight:.2f}, combined={combined_weight:.2f})"


# Example usage and testing
if __name__ == "__main__":
    # Test different scenarios
    current_date = timezone.now().date()
    
    scenarios = [
        ("Current role, 2 years", current_date - timedelta(days=730), None),
        ("Ended 6 months ago, 1 year duration", current_date - timedelta(days=545), current_date - timedelta(days=180)),
        ("Ended 2 years ago, 6 months duration", current_date - timedelta(days=915), current_date - timedelta(days=730)),
        ("Ended 5 years ago, 3 years duration", current_date - timedelta(days=2555), current_date - timedelta(days=1825)),
    ]
    
    for desc, start, end in scenarios:
        weight = calculate_combined_temporal_weight(start, end)
        context = get_temporal_context_description(start, end)
        print(f"{desc}: {weight:.3f}")
        print(f"  {context}")
        print()