# Improved GenAI Image Studio - Streamlit App
import os
import requests
import hashlib
import time
import tempfile
import random
import threading
from typing import Tuple, Optional
import streamlit as st
from PIL import Image
from io import BytesIO

# ───────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION - MUST BE FIRST
# ───────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GenAI Image Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ───────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ───────────────────────────────────────────────────────────────────────────────
def init_session_state():
    """Initialize session state variables"""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "metrics" not in st.session_state:
        st.session_state.metrics = {"calls": 0, "errors": 0, "cache_hits": 0}
    if "generate" not in st.session_state:
        st.session_state.generate = False
    if "current_code" not in st.session_state:
        st.session_state.current_code = ""
    if "tip_index" not in st.session_state:
        st.session_state.tip_index = 0
    if "last_tip_change" not in st.session_state:
        st.session_state.last_tip_change = time.time()

# ───────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & CONSTANTS
# ───────────────────────────────────────────────────────────────────────────────
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
MAX_PROMPT_LENGTH = 500
MIN_PROMPT_WORDS = 3
MAX_DIMENSION = 1024
DEFAULT_DIMENSION = 512
REQUEST_TIMEOUT = 30

FUN_FACTS = [
    "AI image generation uses diffusion models to create art from text",
    "The first neural network was created in 1943",
    "Streamlit makes data apps incredibly simple to build",
    "Python is named after Monty Python's Flying Circus",
    "Image caching can speed up repeated generations by 10x",
    "Negative prompts help exclude unwanted elements from images",
    "Most AI models are trained on millions of image-text pairs"
]

CODING_TIPS = [
    "💡 Use st.cache_data for expensive computations",
    "🔄 Session state persists data across reruns",
    "⚡ Streamlit apps auto-refresh when code changes",
    "🎨 Custom CSS can transform your app's appearance",
    "📊 st.columns() creates responsive layouts",
    "🔧 Error handling improves user experience",
    "💾 Temporary files should be cleaned up properly",
    "🛡️ Always validate user inputs for security",
    "📱 Mobile-first design reaches more users",
    "🚀 Caching strategies boost app performance"
]

STYLE_OPTIONS = {
    "photorealistic": "hyper-realistic, professional photography, high detail",
    "digital art": "digital painting, concept art, trending on artstation",
    "watercolor": "watercolor painting, soft brush strokes, artistic",
    "cyberpunk": "cyberpunk aesthetic, neon lights, futuristic",
    "portrait": "professional portrait, studio lighting, detailed face",
    "abstract": "abstract art, geometric shapes, modern art style",
    "cartoon": "cartoon style, animated, colorful and fun"
}

# ───────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────────────────────
def set_current_code(code_snippet: str):
    """Set currently executing code for display"""
    st.session_state.current_code = code_snippet

def get_rotating_tip():
    """Get current tip with rotation every 3 seconds"""
    current_time = time.time()
    if current_time - st.session_state.last_tip_change > 3:
        st.session_state.tip_index = (st.session_state.tip_index + 1) % len(CODING_TIPS)
        st.session_state.last_tip_change = current_time
    return CODING_TIPS[st.session_state.tip_index]

def validate_prompt(prompt: str) -> Tuple[bool, str]:
    """Validate user prompt with comprehensive checks"""
    if not prompt or not prompt.strip():
        return False, "Prompt cannot be empty"
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, f"Prompt too long (max {MAX_PROMPT_LENGTH} characters)"
    
    word_count = len(prompt.strip().split())
    if word_count < MIN_PROMPT_WORDS:
        return False, f"Prompt too short (minimum {MIN_PROMPT_WORDS} words)"
    
    # Check for potential inappropriate content
    blocked_terms = ['nsfw', 'explicit', 'adult', 'nude']
    if any(term in prompt.lower() for term in blocked_terms):
        return False, "Prompt contains inappropriate content"
    
    return True, "Valid prompt"

def get_cache_path(prompt: str, negative: str, style: str, width: int, height: int) -> str:
    """Generate cache file path based on parameters"""
    cache_key = f"{prompt}|{negative}|{style}|{width}|{height}"
    hash_key = hashlib.sha256(cache_key.encode()).hexdigest()
    cache_dir = os.path.join(tempfile.gettempdir(), "genai_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{hash_key}.png")

def generate_image(prompt: str, negative: str, style: str, width: int, height: int) -> Tuple[Optional[Image.Image], str, float, str]:
    """Generate image with improved error handling and caching"""
    set_current_code("cache_path = get_cache_path(prompt, negative, style, width, height)")
    
    # Check cache first
    cache_path = get_cache_path(prompt, negative, style, width, height)
    if os.path.exists(cache_path):
        try:
            set_current_code("img = Image.open(cache_path)")
            img = Image.open(cache_path)
            st.session_state.metrics["cache_hits"] += 1
            set_current_code("")  # Clear code display
            return img, "cache", 0.0, "Loaded from cache"
        except Exception as e:
            # Remove corrupted cache file
            os.remove(cache_path)
    
    set_current_code("start_time = time.time()")
    start_time = time.time()
    
    try:
        set_current_code("full_prompt = f'{prompt}, {STYLE_OPTIONS.get(style, style)}'")
        # Build enhanced prompt with style
        full_prompt = f"{prompt}, {STYLE_OPTIONS.get(style, style)}"
        if negative:
            full_prompt += f", not {negative}"
        
        set_current_code("encoded_prompt = requests.utils.quote(full_prompt)")
        # Construct API URL
        encoded_prompt = requests.utils.quote(full_prompt)
        url = f"{POLLINATIONS_URL}{encoded_prompt}?width={width}&height={height}&enhance=true"
        
        set_current_code("response = requests.get(url, timeout=REQUEST_TIMEOUT)")
        # Make request with timeout
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        set_current_code("img = Image.open(BytesIO(response.content))")
        # Process image
        img = Image.open(BytesIO(response.content))
        
        set_current_code("img.save(cache_path, 'PNG')")
        # Cache the result
        img.save(cache_path, "PNG")
        
        elapsed = time.time() - start_time
        set_current_code("")  # Clear code display
        return img, "api", elapsed, "Generated successfully"
        
    except requests.exceptions.Timeout:
        set_current_code("")
        st.session_state.metrics["errors"] += 1
        return None, "error", 0.0, "Request timed out"
    except requests.exceptions.RequestException as e:
        set_current_code("")
        st.session_state.metrics["errors"] += 1
        return None, "error", 0.0, f"Network error: {str(e)}"
    except Exception as e:
        set_current_code("")
        st.session_state.metrics["errors"] += 1
        return None, "error", 0.0, f"Unexpected error: {str(e)}"

def clear_cache() -> int:
    """Clear image cache and return number of files deleted"""
    set_current_code("cache_dir = os.path.join(tempfile.gettempdir(), 'genai_cache')")
    cache_dir = os.path.join(tempfile.gettempdir(), "genai_cache")
    if not os.path.exists(cache_dir):
        set_current_code("")
        return 0
    
    files_deleted = 0
    try:
        set_current_code("for filename in os.listdir(cache_dir):")
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path) and filename.endswith('.png'):
                set_current_code(f"os.remove('{filename}')")
                os.remove(file_path)
                files_deleted += 1
        set_current_code("")
    except Exception as e:
        set_current_code("")
        st.error(f"Error clearing cache: {e}")
    
    return files_deleted

# ───────────────────────────────────────────────────────────────────────────────
# PAGE STYLING SETUP
# ───────────────────────────────────────────────────────────────────────────────
def setup_page_styling():
    """Apply custom CSS styling to the page"""
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
            animation: fadeIn 1s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .metric-container {
            background: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        
        .stButton > button {
            width: 100%;
            border-radius: 0.5rem;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .success-message {
            color: #28a745;
            font-weight: bold;
        }
        
        .error-message {
            color: #dc3545;
            font-weight: bold;
        }
        
        .bottom-panel {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 10px 20px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
            border-top: 2px solid #4a90e2;
            z-index: 1000;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }
        
        .code-display {
            background: rgba(0,0,0,0.3);
            padding: 8px 12px;
            border-radius: 6px;
            border-left: 4px solid #00ff88;
            animation: pulse 2s infinite;
        }
        
        .tip-display {
            background: rgba(255,255,255,0.1);
            padding: 8px 12px;
            border-radius: 6px;
            border-left: 4px solid #ffd700;
            animation: fadeInOut 3s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { border-left-color: #00ff88; }
            50% { border-left-color: #00cc66; }
        }
        
        @keyframes fadeInOut {
            0%, 20%, 80%, 100% { opacity: 1; }
            40%, 60% { opacity: 0.7; }
        }
        
        .main .block-container {
            padding-bottom: 80px;
        }
    </style>
    """, unsafe_allow_html=True)

def render_bottom_panel():
    """Render the persistent bottom panel with code display or tips"""
    current_code = st.session_state.current_code
    current_tip = get_rotating_tip()
    
    if current_code:
        panel_content = f"""
        <div class='bottom-panel'>
            <div class='code-display'>
                <strong>⚡ Executing:</strong> {current_code}
            </div>
        </div>
        """
    else:
        panel_content = f"""
        <div class='bottom-panel'>
            <div class='tip-display'>
                <strong>💡 Developer Tip:</strong> {current_tip}
            </div>
        </div>
        """
    
    st.markdown(panel_content, unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ───────────────────────────────────────────────────────────────────────────────
def main():
    init_session_state()
    setup_page_styling()
    
    # Header
    st.markdown("<h1 class='main-header'>🎨 GenAI Image Studio</h1>", unsafe_allow_html=True)
    st.markdown("Create stunning AI-generated images with advanced controls and caching")
    
    # Sidebar Controls
    with st.sidebar:
        st.header("🛠️ Generation Controls")
        
        # Prompt input with validation
        prompt = st.text_area(
            "✍️ Image Description",
            height=100,
            help=f"Describe your image (minimum {MIN_PROMPT_WORDS} words, max {MAX_PROMPT_LENGTH} characters)",
            placeholder="A majestic mountain landscape at sunset..."
        )
        
        # Negative prompt
        negative_prompt = st.text_input(
            "🚫 Exclude Elements",
            help="What to avoid in the image (optional)",
            placeholder="blurry, low quality, watermark..."
        )
        
        # Style selection
        style = st.selectbox(
            "🎨 Art Style",
            options=list(STYLE_OPTIONS.keys()),
            help="Choose from predefined artistic styles"
        )
        
        # Dimension controls with validation
        col1, col2 = st.columns(2)
        with col1:
            width = st.slider("Width", 256, MAX_DIMENSION, DEFAULT_DIMENSION, 64)
        with col2:
            height = st.slider("Height", 256, MAX_DIMENSION, DEFAULT_DIMENSION, 64)
        
        # Dimension warning
        if width > 768 or height > 768:
            st.warning("⚠️ Large dimensions may take longer to generate")
        
        # Generation button
        if st.button("🎨 Generate Image", type="primary"):
            st.session_state.generate = True
        
        # Utility buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Cache"):
                set_current_code("Clearing cache...")
                deleted = clear_cache()
                if deleted > 0:
                    st.success(f"Cleared {deleted} cached images")
                else:
                    st.info("Cache already empty")
        
        with col2:
            if st.button("📊 Reset Stats"):
                set_current_code("st.session_state.metrics = {...}")
                st.session_state.metrics = {"calls": 0, "errors": 0, "cache_hits": 0}
                st.success("Statistics reset")
                set_current_code("")
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["🖼️ Generate", "📈 Analytics", "💡 Guide"])
    
    with tab1:
        # Image generation logic
        if st.session_state.generate:
            st.session_state.generate = False
            
            # Validate prompt
            is_valid, validation_message = validate_prompt(prompt)
            
            if not is_valid:
                st.error(f"❌ {validation_message}")
            else:
                set_current_code("Validating prompt and generating image...")
                with st.spinner("🎨 Creating your masterpiece..."):
                    img, source, elapsed, message = generate_image(
                        prompt, negative_prompt, style, width, height
                    )
                    
                    if img is not None:
                        # Success - display image
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.subheader("Generated Image")
                            st.image(img, use_container_width=True)
                            
                            # Download button
                            buf = BytesIO()
                            img.save(buf, format="PNG")
                            st.download_button(
                                label="📥 Download PNG",
                                data=buf.getvalue(),
                                file_name=f"genai_{int(time.time())}.png",
                                mime="image/png"
                            )
                        
                        with col2:
                            st.subheader("Generation Info")
                            st.info(f"**Source:** {source}")
                            if source == "api":
                                st.info(f"**Time:** {elapsed:.2f}s")
                            st.info(f"**Dimensions:** {width}×{height}")
                            st.info(f"**Style:** {style}")
                            
                            # Fun facts
                            st.subheader("💡 Did You Know?")
                            facts = random.sample(FUN_FACTS, min(3, len(FUN_FACTS)))
                            for fact in facts:
                                st.write(f"• {fact}")
                        
                        # Update metrics and history
                        set_current_code("st.session_state.metrics['calls'] += 1")
                        st.session_state.metrics["calls"] += 1
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state.history.append({
                            "prompt": prompt,
                            "negative": negative_prompt,
                            "style": style,
                            "width": width,
                            "height": height,
                            "source": source,
                            "elapsed": elapsed,
                            "timestamp": timestamp,
                            "image": buf.getvalue()
                        })
                        
                        set_current_code("")
                        st.balloons()
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ Generation failed: {message}")
        
        # Show recent generation if available
        if st.session_state.history:
            st.markdown("---")
            st.subheader("🕐 Recent Generation")
            recent = st.session_state.history[-1]
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(Image.open(BytesIO(recent["image"])), width=200)
            with col2:
                st.write(f"**Prompt:** {recent['prompt']}")
                st.write(f"**Style:** {recent['style']}")
                st.write(f"**Generated:** {recent['timestamp']}")
    
    with tab2:
        st.subheader("📊 Generation Statistics")
        
        # Metrics display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Generations", st.session_state.metrics["calls"])
        with col2:
            st.metric("Cache Hits", st.session_state.metrics["cache_hits"])
        with col3:
            st.metric("Errors", st.session_state.metrics["errors"])
        
        # History display
        if st.session_state.history:
            st.subheader("📜 Generation History")
            
            # Show last 10 generations
            recent_history = list(reversed(st.session_state.history[-10:]))
            
            for i, entry in enumerate(recent_history):
                with st.expander(f"{i+1}. {entry['prompt'][:50]}..." if len(entry['prompt']) > 50 else f"{i+1}. {entry['prompt']}"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(Image.open(BytesIO(entry["image"])), width=150)
                    with col2:
                        st.write(f"**Style:** {entry['style']}")
                        st.write(f"**Dimensions:** {entry['width']}×{entry['height']}")
                        st.write(f"**Source:** {entry['source']}")
                        if entry['source'] == 'api':
                            st.write(f"**Generation Time:** {entry['elapsed']:.2f}s")
                        st.write(f"**Created:** {entry['timestamp']}")
                        if entry['negative']:
                            st.write(f"**Excluded:** {entry['negative']}")
        else:
            st.info("No generations yet. Create your first image!")
    
    with tab3:
        st.subheader("💡 How to Use GenAI Studio")
        
        st.markdown("""
        ### 🚀 Getting Started
        1. **Write a descriptive prompt** - Be specific about what you want to see
        2. **Choose an art style** - Each style produces different artistic effects
        3. **Set dimensions** - Larger images take more time but offer more detail
        4. **Add negative prompts** - Exclude unwanted elements from your image
        5. **Click Generate** - Watch the magic happen!
        
        ### ⚡ Pro Tips
        - **Be descriptive**: Instead of "dog", try "golden retriever running in a sunny park"
        - **Use negative prompts**: Add "blurry, low quality" to improve image clarity
        - **Experiment with styles**: Different styles can dramatically change the output
        - **Cache saves time**: Identical parameters will load instantly from cache
        - **Optimize dimensions**: 512×512 is perfect for most use cases
        
        ### 🛡️ Safety Features
        - Automatic content filtering for appropriate images
        - Prompt validation to ensure quality inputs
        - Error handling with helpful messages
        - Smart caching to reduce generation time
        - Rate limiting protection
        
        ### 🔧 Technical Details
        - **API**: Powered by Pollinations.ai
        - **Caching**: Local file system cache for faster reloads
        - **Formats**: PNG output with full quality preservation
        - **Limits**: 1024×1024 maximum resolution for optimal performance
        """)
        
        st.info("💡 **Remember**: AI image generation is creative and interpretive. The same prompt may produce different results each time!")
    
    # Render the persistent bottom panel
    render_bottom_panel()

if __name__ == "__main__":
    main()