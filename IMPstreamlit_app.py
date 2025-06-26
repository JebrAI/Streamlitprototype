# Enhanced GenAI Image Studio - Streamlit App
import os
import requests
import hashlib
import time
import tempfile
import random
import threading
import json
import base64
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import zipfile

# ───────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION - MUST BE FIRST
# ───────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GenAI Image Studio Pro",
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
        st.session_state.metrics = {"calls": 0, "errors": 0, "cache_hits": 0, "total_time": 0.0}
    if "generate" not in st.session_state:
        st.session_state.generate = False
    if "current_code" not in st.session_state:
        st.session_state.current_code = ""
    if "tip_index" not in st.session_state:
        st.session_state.tip_index = 0
    if "last_tip_change" not in st.session_state:
        st.session_state.last_tip_change = time.time()
    if "favorites" not in st.session_state:
        st.session_state.favorites = []
    if "collections" not in st.session_state:
        st.session_state.collections = {"Default": []}
    if "batch_prompts" not in st.session_state:
        st.session_state.batch_prompts = []
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "default_style": "photorealistic",
            "default_dimensions": (512, 512),
            "auto_enhance": False,
            "save_metadata": True
        }

# ───────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & CONSTANTS
# ───────────────────────────────────────────────────────────────────────────────
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
MAX_PROMPT_LENGTH = 500
MIN_PROMPT_WORDS = 3
MAX_DIMENSION = 1024
DEFAULT_DIMENSION = 512
REQUEST_TIMEOUT = 30
BATCH_LIMIT = 5

FUN_FACTS = [
    "AI image generation uses diffusion models to create art from text",
    "The first neural network was created in 1943",
    "Streamlit makes data apps incredibly simple to build",
    "Python is named after Monty Python's Flying Circus",
    "Image caching can speed up repeated generations by 10x",
    "Negative prompts help exclude unwanted elements from images",
    "Most AI models are trained on millions of image-text pairs",
    "The concept of artificial neural networks was inspired by biological neurons",
    "Generative AI can create images that have never existed before",
    "Color theory plays a crucial role in AI image generation"
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
    "🚀 Caching strategies boost app performance",
    "🎯 Use st.rerun() to refresh the app state",
    "📝 Markdown formatting enhances readability"
]

STYLE_OPTIONS = {
    "photorealistic": "hyper-realistic, professional photography, high detail, 8k resolution",
    "digital art": "digital painting, concept art, trending on artstation, detailed",
    "watercolor": "watercolor painting, soft brush strokes, artistic, flowing colors",
    "cyberpunk": "cyberpunk aesthetic, neon lights, futuristic, dark atmosphere",
    "portrait": "professional portrait, studio lighting, detailed face, high quality",
    "abstract": "abstract art, geometric shapes, modern art style, colorful",
    "cartoon": "cartoon style, animated, colorful and fun, disney-style",
    "oil painting": "oil painting, classical art style, rich textures, masterpiece",
    "sketch": "pencil sketch, hand-drawn, artistic lines, detailed shading",
    "fantasy": "fantasy art, magical, mystical atmosphere, epic fantasy style"
}

PROMPT_TEMPLATES = {
    "Landscape": "A breathtaking {subject} landscape with {lighting} lighting, {weather} weather, ultra-detailed, cinematic",
    "Portrait": "Professional portrait of {subject}, {lighting} lighting, high detail, studio quality, {mood} expression",
    "Abstract": "Abstract {subject} with {colors} colors, {style} style, modern art, geometric patterns",
    "Fantasy": "Fantasy {subject} in a magical {setting}, mystical atmosphere, epic fantasy art style",
    "Sci-Fi": "Futuristic {subject} in a {setting} environment, cyberpunk aesthetic, neon lighting, high-tech"
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

def enhance_image(image: Image.Image, enhance_type: str = "auto") -> Image.Image:
    """Apply image enhancements"""
    if enhance_type == "auto":
        # Auto enhance brightness and contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
    elif enhance_type == "sharpen":
        image = image.filter(ImageFilter.SHARPEN)
    elif enhance_type == "smooth":
        image = image.filter(ImageFilter.SMOOTH)
    
    return image

def generate_image(prompt: str, negative: str, style: str, width: int, height: int, enhance: bool = False) -> Tuple[Optional[Image.Image], str, float, str]:
    """Generate image with improved error handling and caching"""
    set_current_code("cache_path = get_cache_path(prompt, negative, style, width, height)")
    
    # Check cache first
    cache_path = get_cache_path(prompt, negative, style, width, height)
    if os.path.exists(cache_path):
        try:
            set_current_code("img = Image.open(cache_path)")
            img = Image.open(cache_path)
            st.session_state.metrics["cache_hits"] += 1
            set_current_code("")
            return img, "cache", 0.0, "Loaded from cache"
        except Exception as e:
            os.remove(cache_path)
    
    set_current_code("start_time = time.time()")
    start_time = time.time()
    
    try:
        set_current_code("full_prompt = f'{prompt}, {STYLE_OPTIONS.get(style, style)}'")
        full_prompt = f"{prompt}, {STYLE_OPTIONS.get(style, style)}"
        if negative:
            full_prompt += f", not {negative}"
        
        set_current_code("encoded_prompt = requests.utils.quote(full_prompt)")
        encoded_prompt = requests.utils.quote(full_prompt)
        url = f"{POLLINATIONS_URL}{encoded_prompt}?width={width}&height={height}&enhance=true"
        
        set_current_code("response = requests.get(url, timeout=REQUEST_TIMEOUT)")
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        set_current_code("img = Image.open(BytesIO(response.content))")
        img = Image.open(BytesIO(response.content))
        
        # Apply enhancements if requested
        if enhance:
            set_current_code("img = enhance_image(img)")
            img = enhance_image(img)
        
        set_current_code("img.save(cache_path, 'PNG')")
        img.save(cache_path, "PNG")
        
        elapsed = time.time() - start_time
        st.session_state.metrics["total_time"] += elapsed
        set_current_code("")
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

def export_history_to_zip() -> BytesIO:
    """Export generation history as a ZIP file"""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Export metadata
        metadata = {
            "export_date": datetime.now().isoformat(),
            "total_generations": len(st.session_state.history),
            "metrics": st.session_state.metrics
        }
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        # Export images and info
        for i, entry in enumerate(st.session_state.history):
            # Save image
            zip_file.writestr(f"image_{i:03d}.png", entry["image"])
            
            # Save image info
            info = {
                "prompt": entry["prompt"],
                "negative": entry.get("negative", ""),
                "style": entry["style"],
                "dimensions": f"{entry['width']}x{entry['height']}",
                "timestamp": entry["timestamp"],
                "source": entry["source"]
            }
            zip_file.writestr(f"image_{i:03d}_info.json", json.dumps(info, indent=2))
    
    zip_buffer.seek(0)
    return zip_buffer

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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            text-align: center;
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
        
        .favorite-btn {
            background: linear-gradient(45deg, #ff6b6b, #feca57);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .favorite-btn:hover {
            transform: scale(1.05);
        }
        
        .collection-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
            transition: all 0.3s ease;
        }
        
        .collection-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
        
        .template-card {
            background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .template-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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
# NEW FEATURE FUNCTIONS
# ───────────────────────────────────────────────────────────────────────────────
def render_template_builder():
    """Render the template builder interface"""
    st.subheader("🎯 Prompt Templates")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("**Pre-built Templates:**")
        for template_name, template in PROMPT_TEMPLATES.items():
            if st.button(f"📋 {template_name}", key=f"template_{template_name}"):
                return template
        
        st.write("**Custom Template Builder:**")
        custom_template = st.text_area(
            "Create Custom Template",
            placeholder="A {subject} in a {setting} with {lighting} lighting...",
            help="Use {placeholders} for dynamic parts"
        )
        
        if custom_template and st.button("💾 Save Custom Template"):
            if "custom_templates" not in st.session_state:
                st.session_state.custom_templates = {}
            
            template_name = st.text_input("Template Name", key="template_name_input")
            if template_name:
                st.session_state.custom_templates[template_name] = custom_template
                st.success(f"Template '{template_name}' saved!")
    
    with col2:
        if 'custom_templates' in st.session_state and st.session_state.custom_templates:
            st.write("**Your Custom Templates:**")
            for name, template in st.session_state.custom_templates.items():
                if st.button(f"🌟 {name}", key=f"custom_{name}"):
                    return template
    
    return None

def render_batch_generation():
    """Render batch generation interface"""
    st.subheader("🚀 Batch Generation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        batch_prompts = st.text_area(
            "Enter Prompts (one per line)",
            height=150,
            placeholder="Beautiful sunset over mountains\nCyberpunk city at night\nAbstract geometric patterns"
        ).split('\n')
        
        batch_prompts = [p.strip() for p in batch_prompts if p.strip()]
        
        if len(batch_prompts) > BATCH_LIMIT:
            st.warning(f"Too many prompts! Maximum {BATCH_LIMIT} allowed.")
            batch_prompts = batch_prompts[:BATCH_LIMIT]
    
    with col2:
        batch_style = st.selectbox("Batch Style", list(STYLE_OPTIONS.keys()), key="batch_style")
        batch_width = st.select_slider("Batch Width", [256, 512, 768], value=512, key="batch_width")
        batch_height = st.select_slider("Batch Height", [256, 512, 768], value=512, key="batch_height")
        
        if st.button("🎨 Generate Batch", type="primary") and batch_prompts:
            return batch_prompts, batch_style, batch_width, batch_height
    
    if batch_prompts:
        st.info(f"Ready to generate {len(batch_prompts)} images")
    
    return None

def render_collections_manager():
    """Render collections management interface"""
    st.subheader("📁 Collections Manager")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Create new collection
        new_collection = st.text_input("New Collection Name")
        if st.button("➕ Create Collection") and new_collection:
            if new_collection not in st.session_state.collections:
                st.session_state.collections[new_collection] = []
                st.success(f"Collection '{new_collection}' created!")
            else:
                st.warning("Collection already exists!")
        
        # List existing collections
        st.write("**Your Collections:**")
        for collection_name in st.session_state.collections.keys():
            count = len(st.session_state.collections[collection_name])
            if st.button(f"📁 {collection_name} ({count})", key=f"collection_{collection_name}"):
                st.session_state.selected_collection = collection_name
    
    with col2:
        if hasattr(st.session_state, 'selected_collection'):
            collection_name = st.session_state.selected_collection
            collection = st.session_state.collections[collection_name]
            
            st.write(f"**Collection: {collection_name}**")
            
            if collection:
                for i, item in enumerate(collection):
                    with st.expander(f"Image {i+1}: {item['prompt'][:30]}..."):
                        col_a, col_b = st.columns([1, 2])
                        with col_a:
                            st.image(Image.open(BytesIO(item['image'])), width=150)
                        with col_b:
                            st.write(f"**Prompt:** {item['prompt']}")
                            st.write(f"**Style:** {item['style']}")
                            st.write(f"**Created:** {item['timestamp']}")
                            if st.button(f"🗑️ Remove", key=f"remove_{i}"):
                                st.session_state.collections[collection_name].pop(i)
                                st.rerun()
            else:
                st.info("This collection is empty")

# ───────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ───────────────────────────────────────────────────────────────────────────────
def main():
    init_session_state()
    setup_page_styling()
    
    # Header
    st.markdown("<h1 class='main-header'>🎨 GenAI Image Studio Pro</h1>", unsafe_allow_html=True)
    st.markdown("Create stunning AI-generated images with advanced controls, batch processing, and smart collections")
    
    # Sidebar Controls
    with st.sidebar:
        st.header("🛠️ Generation Controls")
        
        # Template selection
        selected_template = render_template_builder()
        
        # Prompt input with validation
        initial_prompt = ""
        if selected_template:
            # Simple template filling
            initial_prompt = selected_template.replace("{subject}", "majestic lion").replace("{lighting}", "golden hour").replace("{setting}", "African savanna").replace("{weather}", "clear").replace("{colors}", "warm").replace("{style}", "realistic").replace("{mood}", "confident")
        
        prompt = st.text_area(
            "✍️ Image Description",
            value=initial_prompt,
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
            index=list(STYLE_OPTIONS.keys()).index(st.session_state.user_preferences["default_style"]),
            help="Choose from predefined artistic styles"
        )
        
        # Dimension controls with validation
        col1, col2 = st.columns(2)
        with col1:
            width = st.slider("Width", 256, MAX_DIMENSION, st.session_state.user_preferences["default_dimensions"][0], 64)
        with col2:
            height = st.slider("Height", 256, MAX_DIMENSION, st.session_state.user_preferences["default_dimensions"][1], 64)
        
        # Enhancement options
        auto_enhance = st.checkbox("🔧 Auto Enhance", value=st.session_state.user_preferences["auto_enhance"])
        
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
                st.session_state.metrics = {"calls": 0, "errors": 0, "cache_hits": 0, "total_time": 0.0}
                st.success("Statistics reset")
                set_current_code("")
    
    # Main content area with enhanced tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🖼️ Generate", 
        "🚀 Batch", 
        "📁 Collections", 
        "⭐ Favorites", 
        "📈 Analytics", 
        "💡 Guide"
    ])
    
    with tab1:
        # Single image generation
        if st.session_state.generate:
            st.session_state.generate = False
            
            is_valid, validation_message = validate_prompt(prompt)
            
            if not is_valid:
                st.error(f"❌ {validation_message}")
            else:
                set_current_code("Validating prompt and generating image...")
                with st.spinner("🎨 Creating your masterpiece..."):
                    img, source, elapsed, message = generate_image(
                        prompt, negative_prompt, style, width, height, auto_enhance
                    )
                    
                    if img is not None:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.subheader("Generated Image")
                            st.image(img, use_container_width=True)
                            
                            # Action buttons
                            col_a, col_b, col_c = st.columns(3)
                            
                            with col_a:
                                buf = BytesIO()
                                img.save(buf, format="PNG")
                                st.download_button(
                                    label="📥 Download PNG",
                                    data=buf.getvalue(),
                                    file_name=f"genai_{int(time.time())}.png",
                                    mime="image/png"
                                )
                            
                            with col_b:
                                if st.button("⭐ Add to Favorites"):
                                    favorite_item = {
                                        "prompt": prompt,
                                        "negative": negative_prompt,
                                        "style": style,
                                        "width": width,
                                        "height": height,
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "image": buf.getvalue()
                                    }
                                    st.session_state.favorites.append(favorite_item)
                                    st.success("Added to favorites!")
                            
                            with col_c:
                                collection_names = list(st.session_state.collections.keys())
                                selected_collection = st.selectbox("Add to Collection", collection_names, key="add_to_collection")
                                if st.button("📁 Add to Collection"):
                                    collection_item = {
                                        "prompt": prompt,
                                        "negative": negative_prompt,
                                        "style": style,
                                        "width": width,
                                        "height": height,
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "image": buf.getvalue()
                                    }
                                    st.session_state.collections[selected_collection].append(collection_item)
                                    st.success(f"Added to {selected_collection}!")
                        
                        with col2:
                            st.subheader("Generation Info")
                            st.info(f"**Source:** {source}")
                            if source == "api":
                                st.info(f"**Time:** {elapsed:.2f}s")
                            st.info(f"**Dimensions:** {width}×{height}")
                            st.info(f"**Style:** {style}")
                            if auto_enhance:
                                st.info("**Enhanced:** ✅")
                            
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
                            "image": buf.getvalue(),
                            "enhanced": auto_enhance
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
                if recent.get('enhanced'):
                    st.write("**Enhanced:** ✅")
    
    with tab2:
        # Batch Generation
        batch_result = render_batch_generation()
        
        if batch_result:
            batch_prompts, batch_style, batch_width, batch_height = batch_result
            
            st.subheader("🚀 Batch Generation Results")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            batch_results = []
            
            for i, batch_prompt in enumerate(batch_prompts):
                status_text.text(f"Generating image {i+1} of {len(batch_prompts)}: {batch_prompt[:50]}...")
                progress_bar.progress((i + 1) / len(batch_prompts))
                
                img, source, elapsed, message = generate_image(
                    batch_prompt, "", batch_style, batch_width, batch_height
                )
                
                if img:
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    batch_results.append({
                        "prompt": batch_prompt,
                        "image": buf.getvalue(),
                        "success": True
                    })
                else:
                    batch_results.append({
                        "prompt": batch_prompt,
                        "error": message,
                        "success": False
                    })
            
            status_text.text("Batch generation complete!")
            
            # Display results
            cols = st.columns(3)
            for i, result in enumerate(batch_results):
                with cols[i % 3]:
                    if result["success"]:
                        st.image(Image.open(BytesIO(result["image"])), caption=result["prompt"][:30])
                        st.download_button(
                            label="📥 Download",
                            data=result["image"],
                            file_name=f"batch_{i+1}.png",
                            mime="image/png",
                            key=f"batch_download_{i}"
                        )
                    else:
                        st.error(f"Failed: {result['prompt'][:30]}")
            
            # Batch download
            if batch_results and any(r["success"] for r in batch_results):
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    for i, result in enumerate(batch_results):
                        if result["success"]:
                            zip_file.writestr(f"batch_{i+1:03d}.png", result["image"])
                
                zip_buffer.seek(0)
                st.download_button(
                    label="📦 Download All as ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"batch_generation_{int(time.time())}.zip",
                    mime="application/zip"
                )
    
    with tab3:
        # Collections Manager
        render_collections_manager()
    
    with tab4:
        # Favorites
        st.subheader("⭐ Your Favorites")
        
        if st.session_state.favorites:
            for i, favorite in enumerate(st.session_state.favorites):
                with st.expander(f"⭐ {favorite['prompt'][:50]}..." if len(favorite['prompt']) > 50 else f"⭐ {favorite['prompt']}"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(Image.open(BytesIO(favorite["image"])), width=200)
                        st.download_button(
                            label="📥 Download",
                            data=favorite["image"],
                            file_name=f"favorite_{i+1}.png",
                            mime="image/png",
                            key=f"fav_download_{i}"
                        )
                    with col2:
                        st.write(f"**Prompt:** {favorite['prompt']}")
                        st.write(f"**Style:** {favorite['style']}")
                        st.write(f"**Dimensions:** {favorite['width']}×{favorite['height']}")
                        st.write(f"**Created:** {favorite['timestamp']}")
                        if favorite.get('negative'):
                            st.write(f"**Excluded:** {favorite['negative']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("🔄 Regenerate", key=f"regen_fav_{i}"):
                                # Set parameters for regeneration
                                st.session_state.generate = True
                                # You could set these in session state to auto-fill the form
                        
                        with col_b:
                            if st.button("🗑️ Remove", key=f"remove_fav_{i}"):
                                st.session_state.favorites.pop(i)
                                st.rerun()
            
            # Bulk actions
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📦 Export Favorites"):
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for i, fav in enumerate(st.session_state.favorites):
                            zip_file.writestr(f"favorite_{i+1:03d}.png", fav["image"])
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download Favorites ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"favorites_{int(time.time())}.zip",
                        mime="application/zip"
                    )
            
            with col2:
                if st.button("🗑️ Clear All Favorites") and st.session_state.favorites:
                    if st.button("⚠️ Confirm Clear All", key="confirm_clear_favs"):
                        st.session_state.favorites = []
                        st.success("All favorites cleared!")
                        st.rerun()
        else:
            st.info("No favorites yet. Generate some images and add them to favorites!")
    
    with tab5:
        # Enhanced Analytics
        st.subheader("📊 Advanced Analytics")
        
        # Enhanced metrics display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="metric-container">
                <h3>{}</h3>
                <p>Total Generations</p>
            </div>
            """.format(st.session_state.metrics["calls"]), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-container">
                <h3>{}</h3>
                <p>Cache Hits</p>
            </div>
            """.format(st.session_state.metrics["cache_hits"]), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-container">
                <h3>{}</h3>
                <p>Errors</p>
            </div>
            """.format(st.session_state.metrics["errors"]), unsafe_allow_html=True)
        
        with col4:
            avg_time = (st.session_state.metrics["total_time"] / max(1, st.session_state.metrics["calls"] - st.session_state.metrics["cache_hits"]))
            st.markdown("""
            <div class="metric-container">
                <h3>{:.1f}s</h3>
                <p>Avg Gen Time</p>
            </div>
            """.format(avg_time), unsafe_allow_html=True)
        
        # Performance charts
        if st.session_state.history:
            st.subheader("📈 Performance Trends")
            
            # Generation time chart
            api_generations = [h for h in st.session_state.history if h["source"] == "api"]
            if api_generations:
                times = [g["elapsed"] for g in api_generations]
                timestamps = [g["timestamp"] for g in api_generations]
                
                chart_data = {
                    "Time": timestamps[-10:],  # Last 10 generations
                    "Generation Time (s)": times[-10:]
                }
                st.line_chart(chart_data, x="Time", y="Generation Time (s)")
            
            # Style usage statistics
            st.subheader("🎨 Style Usage")
            style_counts = {}
            for h in st.session_state.history:
                style = h["style"]
                style_counts[style] = style_counts.get(style, 0) + 1
            
            if style_counts:
                st.bar_chart(style_counts)
            
            # Dimension usage
            st.subheader("📐 Dimension Preferences")
            dimension_counts = {}
            for h in st.session_state.history:
                dim = f"{h['width']}×{h['height']}"
                dimension_counts[dim] = dimension_counts.get(dim, 0) + 1
            
            if dimension_counts:
                st.bar_chart(dimension_counts)
        
        # History display with enhanced features
        if st.session_state.history:
            st.subheader("📜 Generation History")
            
            # History controls
            col1, col2, col3 = st.columns(3)
            with col1:
                history_limit = st.slider("Show Last N Generations", 5, min(50, len(st.session_state.history)), 10)
            with col2:
                if st.button("📦 Export History"):
                    zip_data = export_history_to_zip()
                    st.download_button(
                        label="📥 Download History ZIP",
                        data=zip_data.getvalue(),
                        file_name=f"history_export_{int(time.time())}.zip",
                        mime="application/zip"
                    )
            with col3:
                if st.button("🗑️ Clear History") and st.session_state.history:
                    if st.button("⚠️ Confirm Clear", key="confirm_clear_history"):
                        st.session_state.history = []
                        st.success("History cleared!")
                        st.rerun()
            
            # Show history with pagination
            recent_history = list(reversed(st.session_state.history[-history_limit:]))
            
            for i, entry in enumerate(recent_history):
                with st.expander(f"{i+1}. {entry['prompt'][:60]}..." if len(entry['prompt']) > 60 else f"{i+1}. {entry['prompt']}"):
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
                        if entry.get('negative'):
                            st.write(f"**Excluded:** {entry['negative']}")
                        if entry.get('enhanced'):
                            st.write("**Enhanced:** ✅")
        else:
            st.info("No generations yet. Create your first image!")
    
    with tab6:
        # Enhanced Guide
        st.subheader("💡 Complete Guide to GenAI Studio Pro")
        
        # Quick start guide
        with st.expander("🚀 Quick Start Guide", expanded=True):
            st.markdown("""
            ### Getting Started in 5 Steps
            1. **Write a descriptive prompt** - Be specific about what you want to see
            2. **Choose an art style** - Each style produces different artistic effects  
            3. **Set your dimensions** - Larger images take more time but offer more detail
            4. **Optional: Add negative prompts** - Exclude unwanted elements
            5. **Click Generate** - Watch the magic happen!
            
            **Pro Tip:** Use the template builder for consistent, professional prompts!
            """)
        
        with st.expander("🎯 Advanced Prompt Engineering"):
            st.markdown("""
            ### Crafting Better Prompts
            
            **Structure your prompts like this:**
            `[Subject] + [Action/Pose] + [Environment] + [Lighting] + [Style] + [Quality]`
            
            **Examples:**
            - ❌ "cat" 
            - ✅ "majestic orange tabby cat sitting on a windowsill, golden hour lighting, photorealistic, 8k detail"
            
            **Useful Keywords:**
            - **Quality:** 8k, ultra-detailed, masterpiece, professional
            - **Lighting:** golden hour, dramatic lighting, soft lighting, cinematic
            - **Mood:** serene, dramatic, mysterious, vibrant, ethereal
            - **Composition:** close-up, wide shot, bird's eye view, low angle
            """)
        
        with st.expander("🚀 Batch Generation Tips"):
            st.markdown("""
            ### Efficient Batch Processing
            
            **Best Practices:**
            - Keep prompts varied but use consistent style/dimensions
            - Use templates for systematic variations
            - Limit batches to 5 images for optimal performance
            - Use descriptive first words for easy identification
            
            **Example Batch Set:**
            ```
            Sunset mountain landscape with golden lighting
            Sunrise ocean waves with dramatic clouds  
            Moonlit forest path with mysterious atmosphere
            Starry night sky over rolling hills
            Dawn cityscape with morning mist
            ```
            """)
        
        with st.expander("📁 Collections & Organization"):
            st.markdown("""
            ### Smart Organization
            
            **Collection Ideas:**
            - **By Project:** "Website Headers", "Social Media", "Presentations"
            - **By Style:** "Photorealistic", "Abstract Art", "Illustrations"  
            - **By Subject:** "Landscapes", "Portraits", "Architecture"
            - **By Mood:** "Energetic", "Calm", "Dramatic"
            
            **Tips:**
            - Use favorites for your absolute best generations
            - Create collections before generating for better workflow
            - Export collections as ZIP files for backup
            """)
        
        with st.expander("⚡ Performance Optimization"):
            st.markdown("""
            ### Speed Up Your Workflow
            
            **Cache Benefits:**
            - Identical parameters load instantly
            - Reduces server load and generation time
            - Automatic duplicate detection
            
            **Dimension Guidelines:**
            - **512×512:** Fast, good for previews and social media
            - **768×768:** Balanced quality and speed  
            - **1024×1024:** Highest quality, slower generation
            
            **Network Tips:**
            - Stable internet connection improves reliability
            - Clear cache occasionally to free up disk space
            - Use batch generation during off-peak hours
            """)
        
        with st.expander("🛡️ Safety & Best Practices"):
            st.markdown("""
            ### Safe and Responsible Use
            
            **Content Guidelines:**
            - Avoid inappropriate or offensive content
            - Respect copyright and intellectual property
            - Use generated images responsibly
            
            **Technical Best Practices:**
            - Validate prompts before generation
            - Monitor your usage statistics
            - Keep backups of important generations
            - Clear cache regularly to manage storage
            
            **Troubleshooting:**
            - Check network connection for generation failures
            - Try shorter prompts if getting errors
            - Clear cache if images aren't loading properly
            """)
        
        # Feature overview
        st.subheader("🎨 Feature Overview")
        
        features = [
            ("🖼️ Single Generation", "Create individual high-quality images with full control"),
            ("🚀 Batch Processing", "Generate multiple images efficiently with consistent settings"),
            ("📁 Smart Collections", "Organize your creations into themed collections"),
            ("⭐ Favorites System", "Save and quickly access your best generations"),
            ("🎯 Prompt Templates", "Use pre-built templates or create custom ones"),
            ("📊 Advanced Analytics", "Track performance, usage patterns, and generation history"),
            ("🔧 Auto Enhancement", "Automatically improve image quality with post-processing"),
            ("💾 Smart Caching", "Instant loading of previously generated images"),
            ("📦 Export Tools", "Download individual images or entire collections as ZIP files"),
            ("🎨 Style Variety", "10+ artistic styles from photorealistic to abstract")
        ]
        
        for feature, description in features:
            st.write(f"**{feature}:** {description}")
        
        st.info("💡 **Remember**: AI image generation is creative and interpretive. Experiment with different prompts and styles to discover what works best for your needs!")
    
    # Render the persistent bottom panel
    render_bottom_panel()

if __name__ == "__main__":
    main()