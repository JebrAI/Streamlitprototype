![Preview of GenAI Image Studio](https://github.com/user-attachments/assets/7940d4b8-14da-432e-91ee-bc4ea79ee06a)

# GenAI Image Studio

A Streamlit demo for generating images from text prompts. It includes prompt validation, local caching, custom styling, interactive UI elements and a simple code-execution display.

## Features

- Text prompt input with minimum and maximum checks  
- Optional negative prompt to exclude unwanted elements  
- Multiple art styles: photorealistic, digital art, watercolor, cyberpunk, portrait, abstract, cartoon  
- Width and height sliders up to 1024×1024  
- Client-side caching for faster repeat requests  
- Live metrics (total calls, cache hits, errors) and history of recent generations  
- Rotating developer tips and a bottom panel showing executing code snippets  
- Graceful error handling with clear messages  
- Downloadable PNG output  

## Guardrails and Key Functions

- **Prompt validation** (`validate_prompt`)  
  Checks for nonempty text, word-count and character limits, and filters out blocked terms  
- **Cache path generation** (`get_cache_path`)  
  Creates a SHA-256 based filename under a temp folder for each unique prompt/style/dimensions  
- **Image generation** (`generate_image`)  
  Checks cache first, builds a Pollinations.ai URL, handles timeouts and network errors, processes and saves the image  
- **Cache clearing** (`clear_cache`)  
  Removes all stored PNGs from the local cache folder  
- **Session state init** (`init_session_state`)  
  Ensures keys for history, metrics, flags and tip timers exist to avoid rerun errors  
- **UI styling** (`setup_page_styling`, `render_bottom_panel`)  
  Injects custom CSS for header, buttons, code display panel and rotating tips animation  

## Pros and Cons vs Gradio

**Pros**  
- Fine-grained layout control with sidebars, tabs and columns  
- Rich session-state management for history and metrics  
- Easy to inject custom CSS and HTML  
- Built-in caching decorators and rerun controls  

**Cons**  
- Requires explicit session-state setup  
- Less out-of-the-box for simple demos  
- Slightly steeper learning curve for custom layouts  

## Try It Out!

Live demo:

https://appprototype-fxtmqhhez6ckssxvhddbgb.streamlit.app/

Pro demo (Extended features, small fixes):

https://appprototype-jattxpwwxugyr6keuaqzea.streamlit.app/
## Aaaaaaaand... 
![image](https://github.com/user-attachments/assets/a9f5552b-c742-46bc-b01c-0741ff107ae8)

**Balloons!!**

Each successful generation triggers a confetti effect to celebrate your new art.

## Credits and AI Assistance

- **Idea, Prompts & Debugging**  
  Crafted by the user, leveraging their expertise in Python, machine learning, deep learning, and AI.

- **Core Code Implementation & Design**  
  Generated from the user’s prompts via AI assistance.

- **API Milestones, Project Structure & Testing**  
  Defined and carried out by the project author.


## AI Technology Stack

* **Framework**: Streamlit (Python)
* **Image API**: Pollinations.ai via HTTP GET
* **Caching**: Local file system, SHA-256 filename hashing
* **Image processing**: Pillow (PIL)
* **Language**: Python 3.x
* **UI**: Custom CSS, Streamlit widgets, session state

## Prototype Notice

This is a minimal prototype built with AI assistance. It shows how to combine REST API calls, client-side caching, prompt validation and interactive UI design in Streamlit. It is a proof of concept, not production software.
