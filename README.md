![image](https://github.com/user-attachments/assets/7940d4b8-14da-432e-91ee-bc4ea79ee06a)

# GenAI Image Studio

A prototype web application demonstrating AI-powered image generation through a text-to-image API, built with Python and Streamlit. This project showcases essential development patterns, API integration, user interface design, and performance considerations.

## Overview

GenAI Image Studio allows users to provide descriptive prompts and receive generated images in different artistic styles. The app validates inputs, caches results locally, handles errors gracefully, and tracks usage metrics. It serves as a reference for combining HTTP APIs, session management, and custom styling in a simple, interactive interface.

## Key Features

* Prompt validation with word count and character limits
* Style presets that enhance prompts for diverse visual outcomes
* Negative prompts to exclude unwanted elements from generation
* Local file system cache for faster repeated queries
* Tracking of generation history and basic metrics (calls, cache hits, errors)
* Error handling for API timeouts and network exceptions
* Simple controls for clearing cache and resetting statistics
* Minimalist user interface with sidebar controls, main tabs, and a footer panel for tips or code execution display

## Architecture and Functions

* **API Integration**: Uses the Pollinations.ai HTTP endpoint to generate images from text.
* **Input Validation**: `validate_prompt(prompt)` checks for empty inputs, length constraints, and blocked terms.
* **Caching**: `get_cache_path()` computes a unique file path using SHA256, and `generate_image()` checks and writes to cache before making API calls.
* **Image Generation**: `generate_image(prompt, negative, style, width, height)` handles building the full prompt, making the request, timing execution, caching the result, and reporting status.
* **Session State**: `init_session_state()` defines default values in `st.session_state` for history, metrics, flags, current code, and tip rotation.
* **User Interface**: Implemented with Streamlit components (`st.sidebar`, `st.tabs`, `st.columns`, `st.image`, `st.spinner`, etc.) to structure controls, display images, and show logs.
* **Styling**: Custom CSS applied via `setup_page_styling()` injects styles for headers, buttons, metric containers, and a fixed footer panel.
* **Developer Feedback**: A rotating set of coding tips and live display of executing code snippets in the footer panel.

## Guardrails and Validation

* Enforces a minimum of 3 words and maximum of 500 characters for prompts
* Filters out simple blocked terms like nsfw or explicit content
* Limits image dimensions between 256 and 1024 pixels and warns on large sizes
* Catches and reports API timeouts and general request errors
* Provides clear user messages on validation failures and exceptions

## Technology Stack

* Language: Python 3
* Web Framework: Streamlit for rapid UI development
* HTTP Client: requests library for external API calls
* Image Processing: Pillow (PIL) for reading and writing PNG files
* Caching: Local temporary directory managed with tempfile
* State Management: Streamlit session state for persistence across reruns

## Comparison with Gradio

**Advantages**

* Flexible layout options and custom CSS support
* Built-in session state management suitable for multi-step workflows
* Easy to extend with additional tabs, panels, and custom HTML

**Limitations**

* Requires explicit state initialization and more setup code
* Slightly more complex to configure for very simple demos
* Custom styling relies on HTML injection rather than built-in themes

## AI Assistance and Credits

This README and parts of the code structure were drafted with assistance from an AI language model for navigation, content organization, and wording suggestions.

## Prototype Scope

This project is a minimal prototype designed to illustrate how to connect a text-to-image API, validate user inputs, manage state, and deliver a basic web interface. It is not a complete production application but serves as an educational example of combining APIs, Python programming, and UI design in a single module.

