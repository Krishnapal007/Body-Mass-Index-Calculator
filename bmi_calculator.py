"""
bmi_calculator.py
-----------------
Pure business logic for the BMI Health Tracker: BMI formula, category
classification, colour mapping and input validation.

This module has no GUI or database dependency, so it is easy to unit test.
"""

import math
import re

DISCLAIMER = (
    "Disclaimer: BMI is a screening tool and not a medical diagnosis. "
    "Consult a qualified healthcare professional for medical advice."
)

CATEGORY_ORDER = ["Underweight", "Normal", "Overweight", "Obese"]

# Colour coding required by the project brief
CATEGORY_COLORS = {
    "Underweight": "#2563EB",  # Blue
    "Normal": "#16A34A",       # Green
    "Overweight": "#F97316",   # Orange
    "Obese": "#DC2626",        # Red
}

# Soft background tints used for table rows
CATEGORY_TINTS = {
    "Underweight": "#DBEAFE",
    "Normal": "#DCFCE7",
    "Overweight": "#FFEDD5",
    "Obese": "#FEE2E2",
}

CATEGORY_ADVICE = {
    "Underweight": "Your BMI is below the typical range. A balanced, nutrient-rich "
                   "diet may help. Consider speaking with a healthcare professional.",
    "Normal": "Your BMI is within the typical range. Keep up balanced eating, "
              "regular activity and good sleep.",
    "Overweight": "Your BMI is above the typical range. Regular physical activity and "
                  "balanced nutrition can help. A professional can give personal advice.",
    "Obese": "Your BMI is in the highest range. Consider consulting a healthcare "
             "professional for personalised guidance and support.",
}

# Sensible limits to catch typing mistakes
MIN_WEIGHT, MAX_WEIGHT = 1.0, 500.0   # kg
MIN_HEIGHT, MAX_HEIGHT = 0.5, 2.8     # metres
MAX_USERNAME_LENGTH = 50

_USERNAME_PATTERN = re.compile(r"^[\w .'\-]+$")


class ValidationError(ValueError):
    """Raised when user input is missing or invalid."""


def parse_number(text, field_name):
    """Convert text to a finite float or raise ValidationError."""
    cleaned = (text or "").strip().replace(",", ".")
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty.")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValidationError(
            f"{field_name} must be a number. Letters and symbols are not allowed."
        ) from None
    if math.isnan(value) or math.isinf(value):
        raise ValidationError(f"{field_name} is not a valid number.")
    return value


def validate_username(text):
    """Return a cleaned username or raise ValidationError."""
    name = " ".join((text or "").split())  # trim and collapse spaces
    if not name:
        raise ValidationError("Username cannot be empty.")
    if len(name) > MAX_USERNAME_LENGTH:
        raise ValidationError(f"Username must be at most {MAX_USERNAME_LENGTH} characters.")
    if not _USERNAME_PATTERN.match(name):
        raise ValidationError(
            "Username may contain only letters, numbers, spaces and . _ - ' characters."
        )
    return name


def validate_weight(text):
    """Validate weight in kilograms."""
    weight = parse_number(text, "Weight")
    if weight < 0:
        raise ValidationError("Weight cannot be negative.")
    if weight == 0:
        raise ValidationError("Weight must be greater than zero.")
    if not MIN_WEIGHT <= weight <= MAX_WEIGHT:
        raise ValidationError(
            f"Weight must be between {MIN_WEIGHT:g} and {MAX_WEIGHT:g} kg."
        )
    return weight


def validate_height(text):
    """Validate height in metres."""
    height = parse_number(text, "Height")
    if height < 0:
        raise ValidationError("Height cannot be negative.")
    if height == 0:
        raise ValidationError("Height cannot be zero (it would cause division by zero).")
    if height > 3:
        raise ValidationError(
            "Height looks too large. Enter height in metres, for example 1.75 (not 175)."
        )
    if not MIN_HEIGHT <= height <= MAX_HEIGHT:
        raise ValidationError(
            f"Height must be between {MIN_HEIGHT:g} and {MAX_HEIGHT:g} metres."
        )
    return height


def validate_inputs(username, weight_text, height_text):
    """Validate all calculator inputs. Returns (username, weight, height)."""
    return (
        validate_username(username),
        validate_weight(weight_text),
        validate_height(height_text),
    )


def calculate_bmi(weight, height):
    """BMI = weight / (height ** 2), rounded to 2 decimal places."""
    if weight <= 0 or height <= 0:
        raise ValidationError("Weight and height must be greater than zero.")
    return round(weight / (height ** 2), 2)


def get_category(bmi):
    """Classify a BMI value (the 2-decimal value shown to the user)."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def get_color(category):
    """Return the hex colour for a BMI category."""
    return CATEGORY_COLORS.get(category, "#64748B")
