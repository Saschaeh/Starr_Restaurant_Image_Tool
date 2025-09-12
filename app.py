import streamlit as st
from PIL import Image
import os
import zipfile
import io
import base64

# Function to get base64 of image
def get_base64_of_bin_file(bin_file_path):
    with open(bin_file_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Mapping of image base names to target dimensions (width, height) and aspect ratio
image_mappings = {
    'Hero_Image_Desktop': (1920, 1080, 16/9),  # 16:9 - Horizontal
    'Hero_Image_Mobile': (1080, 680, 1080/680),  # ~1.588 - Horizontal
    'Concept_1': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Concept_2': (1080, 1080, 1),  # 1:1 - Square
    'Concept_3': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Cuisine_1': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Cuisine_2': (1080, 1080, 1),  # 1:1 - Square
    'Chef_1': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Chef_2': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Chef_3': (900, 1200, 900/1200),  # 3:4 - Vertical
    'Menu_1': (1920, 1080, 16/9),  # 16:9 - Horizontal
}

def resize_and_crop(img, target_width, target_height):
    original_width, original_height = img.size
    target_ratio = target_width / target_height
    original_ratio = original_width / original_height
    
    if original_ratio > target_ratio:
        # Image is wider: resize based on height, crop width
        new_height = target_height
        new_width = int(new_height * original_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Center crop
        left = (new_width - target_width) // 2
        img = img.crop((left, 0, left + target_width, new_height))
    else:
        # Image is taller: resize based on width, crop height
        new_width = target_width
        new_height = int(new_width / original_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Center crop
        top = (new_height - target_height) // 2
        img = img.crop((0, top, target_width, top + target_height))
    
    return img

def is_black_and_white(img):
    # Check if the image mode is grayscale ('L' or '1')
    if img.mode in ('L', '1'):
        return True
    
    # Convert to RGB if not already, and check if all pixels are grayscale (R==G==B) with tolerance
    img_rgb = img.convert('RGB')
    pixels = list(img_rgb.getdata())
    return all(abs(r - g) < 15 and abs(g - b) < 15 and abs(b - r) < 15 for r, g, b in pixels)  # Increased tolerance to 15

# Streamlit app
st.title("Starr Restaurant Image Editor")

# Add background image styling
bg_img = get_base64_of_bin_file('bg.jpg')  # Use relative path for deployment
css = f"""
<style>
[data-testid="stAppViewContainer"] {{
    position: relative;
    background-image: url("data:image/jpeg;base64,{bg_img}");
    background-size: cover;
    background-position: center;
}}
[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.4);
    z-index: 1;
}}
[data-testid="stAppViewContainer"] > * {{
    position: relative;
    z-index: 2;
    color: white !important;
}}
div.stButton > button {{
    width: 80% !important; /* Reduce width by 20% (from 100% to 80%) */
    float: right;
}}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# Step 1: Input restaurant name with Apply button right-aligned and thinner
with st.form(key="restaurant_form"):
    restaurant_name = st.text_input("Enter Restaurant Name", help="This name will be the first word of the resized image filenames and should avoid special characters for best results.")
    apply_button = st.form_submit_button(label="Apply", help="Click to apply the restaurant name")
    if apply_button:
        if not restaurant_name:
            st.error("Please enter a restaurant name to proceed.")
        else:
            st.session_state.restaurant_name_cleaned = restaurant_name.replace(' ', '_').replace('[^a-zA-Z0-9_]', '')
            st.rerun()  # Rerun to update the app state

# Use the cleaned restaurant name from session state
restaurant_name = st.session_state.get("restaurant_name_cleaned")
if not restaurant_name:
    st.stop()

# Step 2: Upload fields with descriptions and styled blocks
uploaded_files = {}
fields = [
    ('Hero_Image_Desktop', "Main Desktop Banner Image (Horizontal)", "Image Requirement: Horizontal image with estimated aspect ratio of 16:9."),
    ('Hero_Image_Mobile', "Main Mobile Banner Image (Horizontal)", "This can be the same as Desktop, but ideally, we want an image that works better on smaller screens. Image Requirement: Horizontal image with estimated aspect ratio of 1.588:1."),
    ('Concept_1', "First Concept Image (Vertical)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Concept_2', "Second Concept Image (Square)", "Image Requirement: Square image with estimated aspect ratio of 1:1."),
    ('Concept_3', "Third Concept Image (Vertical)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Cuisine_1', "First Cuisine Image (Vertical)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Cuisine_2', "Second Cuisine Image (Square)", "Image Requirement: Square image with estimated aspect ratio of 1:1."),
    ('Chef_1', "First Chef Image (Vertical + Black&White) (required)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Chef_2', "Second Chef Image (Vertical + Black&White) (Optional)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Chef_3', "Third Chef Image (Vertical + Black&White) (Optional)", "Image Requirement: Vertical image with estimated aspect ratio of 3:4."),
    ('Menu_1', "Menu Image (Horizontal)", "Image Requirement: Horizontal image with estimated aspect ratio of 16:9.")
]

for i, (name, header, description) in enumerate(fields):
    with st.container():
        # Apply custom styling to the container with larger headers
        st.markdown(f"""
            <style>
            div.stContainer-{{id}} {{
                border: 2px solid #ccc;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 5px;
            }}
            div.stContainer-{{id}} h4 {{
                font-size: 1.2em; /* 20% larger than default */
            }}
            </style>
        """, unsafe_allow_html=True)
        st.write(f"**{header}**")
        st.write(description)
        uploaded_files[name] = st.file_uploader("", type=['jpg', 'jpeg', 'png'], key=name, label_visibility="collapsed")
        
        # Clear previous messages for this field
        st.empty()  # Clear previous warnings or success messages
        
        # Check aspect ratio and black & white for all Chef images
        if uploaded_files[name]:
            img = Image.open(uploaded_files[name])
            # Handle EXIF orientation
            exif = img._getexif()
            if exif and 274 in exif:  # Orientation tag
                orientation = exif[274]
                if orientation == 3:  # 180° rotation
                    img = img.rotate(180, expand=True)
                elif orientation == 6:  # 90° clockwise
                    img = img.rotate(-90, expand=True)
                elif orientation == 8:  # 90° counterclockwise
                    img = img.rotate(90, expand=True)
            width, height = img.size
            original_ratio = width / height
            target_width, target_height, target_ratio = image_mappings[name]
            allowed_deviation = target_ratio * 0.2  # 20% deviation
            
            # Aspect ratio check
            aspect_ok = abs(original_ratio - target_ratio) <= allowed_deviation
            
            # Black and white check for Chef images with loading spinner
            is_chef = name in ['Chef_1', 'Chef_2', 'Chef_3']
            bw_ok = False
            if is_chef:
                with st.spinner('Checking if image is grayscale...'):
                    bw_ok = is_black_and_white(img)
            else:
                bw_ok = True  # Non-Chef images don't need this check
            
            # Show warnings independently
            if not aspect_ok:
                st.warning("💡Oops Funky Ingredients: You can use this but the image's aspect ratio deviates by 20% from the target. Processing may crop substantially and not look as delicious as intended.")
            
            if is_chef and not bw_ok:
                st.warning("💡Brand guidelines strongly suggest Black&White images of the chefs to keep with the editorial look.")
            
            # Show success only if both conditions are met for Chef images, or just aspect for others
            if aspect_ok and (not is_chef or bw_ok):
                st.success("✅ Perfect, looks delicious!")
    
    # Add horizontal line after each section (except the last one)
    if i < len(fields) - 1:
        st.markdown("<hr style='border: 1px solid #ccc; margin: 10px 0;'>", unsafe_allow_html=True)

# Validation
missing_required = [name for name, header, desc in fields if name not in ['Chef_2', 'Chef_3'] and not uploaded_files[name]]
chef_count = sum(1 for name in ['Chef_1', 'Chef_2', 'Chef_3'] if uploaded_files[name])
if missing_required or chef_count == 0:
    if missing_required:
        st.error(f"Missing required fields: {', '.join(missing_required)}.")
    if chef_count == 0:
        st.error("At least one Chef image (Chef_1, Chef_2, or Chef_3) is required.")
    st.stop()

# Process button
if st.button("Process Images"):
    progress_bar = st.progress(0)
    total_files = len([f for f in uploaded_files.values() if f])
    if total_files > 0:
        zip_buffer = io.BytesIO()  # Moved outside the loop to define it once
        zip_file = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED)
        for i, (name, file) in enumerate(uploaded_files.items()):
            if file:
                target_width, target_height, _ = image_mappings[name]
                img = Image.open(file)
                resized_img = resize_and_crop(img, target_width, target_height)
                
                # Map file extension to PIL-compatible format
                ext = file.name.split('.')[-1].lower()
                format_map = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG'}
                img_format = format_map.get(ext, 'JPEG')  # Default to JPEG if extension not recognized
                
                # New filename
                new_filename = f"{restaurant_name}_{name}_{target_width}x{target_height}.{ext}"
                
                # Save to in-memory buffer and add to ZIP under 'Resized' folder
                img_buffer = io.BytesIO()
                resized_img.save(img_buffer, format=img_format, quality=95)
                img_buffer.seek(0)
                zip_file.writestr(f"Resized/{new_filename}", img_buffer.read())
            
            # Update progress, clamped between 0.0 and 1.0
            progress = min(max((i + 1) / total_files, 0.0), 1.0)
            progress_bar.progress(progress)
        zip_file.close()
    
    # Provide download link
    zip_buffer.seek(0)
    st.success("Processing complete!")
    st.download_button(
        label="Download ZIP of Resized Images",
        data=zip_buffer,
        file_name=f"{restaurant_name}_resized_images.zip",
        mime="application/zip"
    )

