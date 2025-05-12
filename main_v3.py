import os
import sys
import json
import cv2
import numpy as np
import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image, ImageTk
import colorsys
import threading
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union
import shutil

# Set the appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ColorVariationGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Variation Generator")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set minimum window size
        self.root.minsize(1000, 700)
        
        # Image processing variables
        self.input_image_path = None
        self.input_image = None
        self.cv_image = None
        self.preview_image = None
        self.processing_thread = None
        self.is_processing = False
        
        # App config and history
        self.config_file = os.path.join(os.path.expanduser("~"), ".color_variation_config.json")
        self.load_config()
        
        # Create the main layout
        self.create_layout()
        
        # Set up drag and drop
        self.setup_drag_drop()
        
        # Add a window resize event handler for responsive UI
        self.root.bind("<Configure>", self.on_window_resize)
        
    def create_layout(self):
        # Create main frames
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel: Control Panel
        self.control_frame = ctk.CTkFrame(self.main_frame)
        self.control_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # Right panel: Preview and Output
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side="right", fill="both", expand=True)
        
        # Top right: Preview area
        self.preview_frame = ctk.CTkFrame(self.right_frame)
        self.preview_frame.pack(side="top", fill="both", expand=True, pady=(0, 10))
        
        # Bottom right: Log/output area
        self.log_frame = ctk.CTkFrame(self.right_frame)
        self.log_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        # Create control panel elements
        self.create_control_panel()
        
        # Create preview area
        self.create_preview_area()
        
        # Create log area
        self.create_log_area()
        
    def create_control_panel(self):
        # Control panel title
        self.control_title = ctk.CTkLabel(self.control_frame, text="Control Panel", font=("Arial", 16, "bold"))
        self.control_title.pack(pady=(10, 20))
        
        # Image selection
        self.file_frame = ctk.CTkFrame(self.control_frame)
        self.file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_label = ctk.CTkLabel(self.file_frame, text="Input Image:")
        self.file_label.pack(anchor="w", pady=(5, 0))
        
        self.file_path = ctk.CTkLabel(self.file_frame, text="No file selected", wraplength=200)
        self.file_path.pack(anchor="w", pady=(0, 5))
        
        self.file_button = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file)
        self.file_button.pack(fill="x", pady=5)
        
        # Separator
        self.separator1 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator1.pack(fill="x", padx=10, pady=10)
        
        # Variation parameters
        self.param_frame = ctk.CTkFrame(self.control_frame)
        self.param_frame.pack(fill="x", padx=10, pady=5)
        
        self.saturation_label = ctk.CTkLabel(self.param_frame, text="Saturation Levels:")
        self.saturation_label.pack(anchor="w", pady=(5, 0))
        
        self.saturation_value = ctk.IntVar(value=self.config.get("saturation_levels", 3))
        self.saturation_entry = ctk.CTkEntry(self.param_frame, textvariable=self.saturation_value)
        self.saturation_entry.pack(fill="x", pady=5)
        
        self.hue_label = ctk.CTkLabel(self.param_frame, text="Hue Variations:")
        self.hue_label.pack(anchor="w", pady=(5, 0))
        
        self.hue_value = ctk.IntVar(value=self.config.get("hue_variations", 10))
        self.hue_entry = ctk.CTkEntry(self.param_frame, textvariable=self.hue_value)
        self.hue_entry.pack(fill="x", pady=5)
        
        # Separator
        self.separator2 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator2.pack(fill="x", padx=10, pady=10)
        
        # RGB Adjustment
        self.rgb_frame = ctk.CTkFrame(self.control_frame)
        self.rgb_frame.pack(fill="x", padx=10, pady=5)
        
        self.rgb_label = ctk.CTkLabel(self.rgb_frame, text="RGB Adjustment for Low Saturation:")
        self.rgb_label.pack(anchor="w", pady=(5, 0))
        
        # Red channel slider
        self.red_label = ctk.CTkLabel(self.rgb_frame, text=f"R: {self.config.get('red_value', 100)}%")
        self.red_label.pack(anchor="w", pady=(5, 0))
        
        self.red_value = ctk.DoubleVar(value=self.config.get("red_value", 100))
        self.red_slider = ctk.CTkSlider(self.rgb_frame, from_=0, to=200, 
                                        variable=self.red_value, 
                                        command=lambda val: self.update_rgb_label('red', val))
        self.red_slider.pack(fill="x", pady=5)
        
        # Green channel slider
        self.green_label = ctk.CTkLabel(self.rgb_frame, text=f"G: {self.config.get('green_value', 100)}%")
        self.green_label.pack(anchor="w", pady=(5, 0))
        
        self.green_value = ctk.DoubleVar(value=self.config.get("green_value", 100))
        self.green_slider = ctk.CTkSlider(self.rgb_frame, from_=0, to=200, 
                                          variable=self.green_value, 
                                          command=lambda val: self.update_rgb_label('green', val))
        self.green_slider.pack(fill="x", pady=5)
        
        # Blue channel slider
        self.blue_label = ctk.CTkLabel(self.rgb_frame, text=f"B: {self.config.get('blue_value', 100)}%")
        self.blue_label.pack(anchor="w", pady=(5, 0))
        
        self.blue_value = ctk.DoubleVar(value=self.config.get("blue_value", 100))
        self.blue_slider = ctk.CTkSlider(self.rgb_frame, from_=0, to=200, 
                                         variable=self.blue_value, 
                                         command=lambda val: self.update_rgb_label('blue', val))
        self.blue_slider.pack(fill="x", pady=5)
        
        # Separator
        self.separator3 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator3.pack(fill="x", padx=10, pady=10)
        
        # Grayscale-Skip options
        self.grayscale_frame = ctk.CTkFrame(self.control_frame)
        self.grayscale_frame.pack(fill="x", padx=10, pady=5)
        
        self.grayscale_label = ctk.CTkLabel(self.grayscale_frame, text="Grayscale-Skip Modes:")
        self.grayscale_label.pack(anchor="w", pady=(5, 0))
        
        self.grayscale_mode = ctk.IntVar(value=self.config.get("grayscale_mode", 0))
        
        self.no_skip_radio = ctk.CTkRadioButton(self.grayscale_frame, text="No Skip", 
                                               variable=self.grayscale_mode, value=0)
        self.no_skip_radio.pack(anchor="w", pady=2)
        
        self.exact_skip_radio = ctk.CTkRadioButton(self.grayscale_frame, text="Exact Grayscale Skip", 
                                                  variable=self.grayscale_mode, value=1)
        self.exact_skip_radio.pack(anchor="w", pady=2)
        
        self.near_skip_radio = ctk.CTkRadioButton(self.grayscale_frame, text="Near Grayscale Skip", 
                                                 variable=self.grayscale_mode, value=2)
        self.near_skip_radio.pack(anchor="w", pady=2)
        
        self.threshold_label = ctk.CTkLabel(self.grayscale_frame, text="Threshold:")
        self.threshold_label.pack(anchor="w", pady=(5, 0))
        
        self.threshold_value = ctk.IntVar(value=self.config.get("threshold", 10))
        self.threshold_slider = ctk.CTkSlider(self.grayscale_frame, from_=0, to=50, 
                                             variable=self.threshold_value)
        self.threshold_slider.pack(fill="x", pady=5)
        
        self.threshold_display = ctk.CTkLabel(self.grayscale_frame, 
                                             text=f"Threshold Value: {self.threshold_value.get()}")
        self.threshold_display.pack(anchor="w", pady=(0, 5))
        
        self.threshold_value.trace_add("write", self.update_threshold_display)
        
        # Separator
        self.separator4 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator4.pack(fill="x", padx=10, pady=10)
        
        # Transparency options
        self.transparency_frame = ctk.CTkFrame(self.control_frame)
        self.transparency_frame.pack(fill="x", padx=10, pady=5)
        
        self.transparency_label = ctk.CTkLabel(self.transparency_frame, text="Transparency Processing:")
        self.transparency_label.pack(anchor="w", pady=(5, 0))
        
        self.transparency_mode = ctk.IntVar(value=self.config.get("transparency_mode", 0))
        
        self.all_pixels_radio = ctk.CTkRadioButton(self.transparency_frame, text="Process All Pixels", 
                                                  variable=self.transparency_mode, value=0)
        self.all_pixels_radio.pack(anchor="w", pady=2)
        
        self.transparent_radio = ctk.CTkRadioButton(self.transparency_frame, text="Only Transparent", 
                                                   variable=self.transparency_mode, value=1)
        self.transparent_radio.pack(anchor="w", pady=2)
        
        self.non_transparent_radio = ctk.CTkRadioButton(self.transparency_frame, text="Only Non-Transparent", 
                                                      variable=self.transparency_mode, value=2)
        self.non_transparent_radio.pack(anchor="w", pady=2)
        
        # Separator
        self.separator5 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator5.pack(fill="x", padx=10, pady=10)
        
        # Output options
        self.output_frame = ctk.CTkFrame(self.control_frame)
        self.output_frame.pack(fill="x", padx=10, pady=5)
        
        self.output_label = ctk.CTkLabel(self.output_frame, text="Output Settings:")
        self.output_label.pack(anchor="w", pady=(5, 0))
        
        self.output_dir_var = ctk.StringVar(value=self.config.get("output_dir", ""))
        self.output_dir_label = ctk.CTkLabel(self.output_frame, text="Output Directory:")
        self.output_dir_label.pack(anchor="w", pady=(5, 0))
        
        self.output_dir_path = ctk.CTkLabel(self.output_frame, text="Same as input", wraplength=200)
        self.output_dir_path.pack(anchor="w", pady=(0, 5))
        
        self.output_dir_button = ctk.CTkButton(self.output_frame, text="Choose Output Directory", 
                                              command=self.choose_output_dir)
        self.output_dir_button.pack(fill="x", pady=5)
        
        # Variation name prefix
        self.prefix_label = ctk.CTkLabel(self.output_frame, text="Variation Prefix:")
        self.prefix_label.pack(anchor="w", pady=(5, 0))
        
        self.prefix_value = ctk.StringVar(value=self.config.get("prefix", "variation"))
        self.prefix_entry = ctk.CTkEntry(self.output_frame, textvariable=self.prefix_value)
        self.prefix_entry.pack(fill="x", pady=5)
        
        # Separator
        self.separator6 = ctk.CTkFrame(self.control_frame, height=2, fg_color="gray30")
        self.separator6.pack(fill="x", padx=10, pady=10)
        
        # Process button
        self.process_button = ctk.CTkButton(self.control_frame, text="Start Processing", 
                                           command=self.start_processing, fg_color="green", 
                                           hover_color="dark green", height=40)
        self.process_button.pack(fill="x", padx=10, pady=10)
        
        # Cancel button (initially disabled)
        self.cancel_button = ctk.CTkButton(self.control_frame, text="Cancel", 
                                          command=self.cancel_processing, fg_color="red", 
                                          hover_color="dark red", state="disabled")
        self.cancel_button.pack(fill="x", padx=10, pady=5)
        
    def create_preview_area(self):
        # Preview area title
        self.preview_title = ctk.CTkLabel(self.preview_frame, text="Image Preview", font=("Arial", 16, "bold"))
        self.preview_title.pack(pady=10)
        
        # Preview canvas
        self.preview_canvas_frame = ctk.CTkFrame(self.preview_frame)
        self.preview_canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.preview_canvas = ctk.CTkCanvas(self.preview_canvas_frame, background="#2b2b2b", 
                                          highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        
        # Placeholder text for empty canvas
        self.preview_canvas.create_text(150, 150, text="Drag and drop an image here\nor click Browse", 
                                       fill="white", font=("Arial", 14))
    
    def create_log_area(self):
        # Log area title
        self.log_title = ctk.CTkLabel(self.log_frame, text="Processing Log", font=("Arial", 14, "bold"))
        self.log_title.pack(anchor="w", pady=(5, 0))
        
        # Log text area
        self.log_text = ctk.CTkTextbox(self.log_frame, height=100, font=("Courier", 12))
        self.log_text.pack(fill="both", expand=True, pady=5)
        self.log_text.configure(state="disabled")
        
        # Progress bar
        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(self.log_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(self.log_frame, text="0%")
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
    def setup_drag_drop(self):
        try:
            # Detect platform
            if sys.platform == 'win32':
                # Windows drag and drop using TkDND
                # First try if tkinterdnd2 is installed
                try:
                    from tkinterdnd2 import TkinterDnD, DND_FILES
                    # Make the root compatible with tkinterdnd2
                    self.root = TkinterDnD.Tk(className='ColorVariationGenerator')
                    self.preview_canvas.drop_target_register(DND_FILES)
                    self.preview_canvas.dnd_bind('<<Drop>>', self.on_drop)
                except ImportError:
                    self.log("TkinterDnD not available. Drag and drop disabled.", level="warning")
                    
            elif sys.platform == 'darwin':
                # macOS drag and drop
                self.preview_canvas.bind("<Button-1>", self.on_canvas_click)
                
            elif sys.platform.startswith('linux'):
                # Linux drag and drop
                try:
                    from tkinterdnd2 import TkinterDnD, DND_FILES
                    # Make the root compatible with tkinterdnd2
                    self.root = TkinterDnD.Tk(className='ColorVariationGenerator')
                    self.preview_canvas.drop_target_register(DND_FILES)
                    self.preview_canvas.dnd_bind('<<Drop>>', self.on_drop)
                except ImportError:
                    self.log("TkinterDnD not available. Drag and drop disabled.", level="warning")
        except Exception as e:
            self.log(f"Error setting up drag and drop: {e}", level="error")

    def on_drop(self, event):
        file_path = event.data
        
        # Handle file path based on OS
        if sys.platform == 'win32':
            # Windows paths might be enclosed in {} or have file:/// prefix
            file_path = file_path.strip('{}')
            if file_path.startswith('file:///'):
                file_path = file_path[8:]
        
        # Check if it's an image file
        if self.is_valid_image_file(file_path):
            self.load_image(file_path)
        else:
            self.log("Not a valid image file. Please select a PNG, JPEG, or JPG.", level="error")
    
    def on_canvas_click(self, event):
        self.browse_file()
    
    def is_valid_image_file(self, file_path: str) -> bool:
        """Check if the file is a valid image file (PNG, JPEG, or JPG)."""
        try:
            if not os.path.isfile(file_path):
                return False
            
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg']:
                return False
            
            # Try to open with PIL to verify it's a valid image
            Image.open(file_path).verify()
            return True
        except Exception:
            return False
    
    def browse_file(self):
        """Open a file dialog to select an image file."""
        file_types = [('Image files', '*.png *.jpg *.jpeg')]
        file_path = filedialog.askopenfilename(title="Select Image File", filetypes=file_types)
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, file_path: str):
        """Load an image from the given file path."""
        try:
            self.input_image_path = file_path
            self.file_path.configure(text=os.path.basename(file_path))
            
            # Load with PIL
            self.input_image = Image.open(file_path)
            
            # Convert to OpenCV format
            if self.input_image.mode == 'RGBA':
                self.cv_image = cv2.cvtColor(np.array(self.input_image), cv2.COLOR_RGBA2BGRA)
            else:
                self.cv_image = cv2.cvtColor(np.array(self.input_image), cv2.COLOR_RGB2BGR)
            
            # Update preview
            self.update_preview()
            
            # Update output directory path if not explicitly set
            if not self.output_dir_var.get():
                self.output_dir_var.set(os.path.dirname(file_path))
                self.output_dir_path.configure(text=os.path.dirname(file_path))
            
            self.log(f"Loaded image: {os.path.basename(file_path)}", level="info")
            
        except Exception as e:
            self.log(f"Error loading image: {e}", level="error")
    
    def update_preview(self):
        """Update the preview canvas with the current image."""
        if self.input_image is None:
            return
        
        # Clear canvas
        self.preview_canvas.delete("all")
        
        # Get canvas dimensions
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # If canvas is not properly initialized yet, use default size
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 300
        
        # Calculate aspect ratio
        img_width, img_height = self.input_image.size
        img_ratio = img_width / img_height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            # Image is wider than canvas
            new_width = canvas_width
            new_height = int(canvas_width / img_ratio)
        else:
            # Image is taller than canvas
            new_height = canvas_height
            new_width = int(canvas_height * img_ratio)
        
        # Create a copy of the image for preview
        self.preview_image = self.input_image.copy()
        
        # Apply RGB adjustments if needed (for preview only)
        red_factor = self.red_value.get() / 100.0
        green_factor = self.green_value.get() / 100.0
        blue_factor = self.blue_value.get() / 100.0
        
        if red_factor != 1.0 or green_factor != 1.0 or blue_factor != 1.0:
            # Convert to numpy array for faster processing
            img_array = np.array(self.preview_image)
            
            # Apply RGB adjustments based on mode
            if len(img_array.shape) == 3:  # Color image
                if img_array.shape[2] >= 3:  # RGB or RGBA
                    img_array[..., 0] = np.clip(img_array[..., 0] * red_factor, 0, 255).astype(np.uint8)
                    img_array[..., 1] = np.clip(img_array[..., 1] * green_factor, 0, 255).astype(np.uint8)
                    img_array[..., 2] = np.clip(img_array[..., 2] * blue_factor, 0, 255).astype(np.uint8)
                    
            # Convert back to PIL Image
            self.preview_image = Image.fromarray(img_array)
        
        # Resize for display
        display_img = self.preview_image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to PhotoImage
        self.tk_image = ImageTk.PhotoImage(display_img)
        
        # Calculate position to center the image
        x_position = (canvas_width - new_width) // 2
        y_position = (canvas_height - new_height) // 2
        
        # Create image on canvas
        self.preview_canvas.create_image(x_position, y_position, anchor="nw", image=self.tk_image)
    
    def choose_output_dir(self):
        """Open a dialog to choose the output directory."""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        
        if output_dir:
            self.output_dir_var.set(output_dir)
            self.output_dir_path.configure(text=output_dir)
    
    def log(self, message: str, level: str = "info"):
        """Add a message to the log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_prefix = {
            "info": "[INFO]",
            "warning": "[WARNING]",
            "error": "[ERROR]",
            "success": "[SUCCESS]"
        }.get(level, "[INFO]")
        
        log_message = f"{timestamp} {level_prefix} {message}\n"
        
        # Add color based on level
        level_colors = {
            "info": "white",
            "warning": "#FFA500",  # Orange
            "error": "#FF0000",    # Red
            "success": "#00FF00"   # Green
        }
        
        # Enable the text widget for editing
        self.log_text.configure(state="normal")
        
        # Insert the log message
        self.log_text.insert("end", log_message)
        
        # Apply color tag
        start_index = self.log_text.index("end-1l linestart")
        end_index = self.log_text.index("end-1c")
        self.log_text.tag_add(level, start_index, end_index)
        self.log_text.tag_config(level, foreground=level_colors.get(level, "white"))
        
        # Auto-scroll to the bottom
        self.log_text.see("end")
        
        # Disable the text widget again
        self.log_text.configure(state="disabled")
        
        # Update the UI
        self.root.update_idletasks()
    
    def update_threshold_display(self, *args):
        """Update the threshold display label."""
        self.threshold_display.configure(text=f"Threshold Value: {self.threshold_value.get()}")
    
    def update_rgb_label(self, channel: str, value: float):
        """Update the RGB slider labels."""
        value = int(value)
        if channel == 'red':
            self.red_label.configure(text=f"R: {value}%")
        elif channel == 'green':
            self.green_label.configure(text=f"G: {value}%")
        elif channel == 'blue':
            self.blue_label.configure(text=f"B: {value}%")
        
        # Update preview with new RGB values
        if self.input_image is not None:
            self.update_preview()
    
    def start_processing(self):
        """Start the image processing in a separate thread."""
        if self.input_image_path is None:
            self.log("No image selected. Please select an image first.", level="error")
            return
        
        if self.is_processing:
            self.log("Processing already in progress.", level="warning")
            return
        
        # Save current settings to config
        self.update_config()
        
        # Update UI for processing state
        self.process_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.is_processing = True
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        
        # Clear previous log entries
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_image)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def cancel_processing(self):
        """Cancel the current processing operation."""
        if self.is_processing:
            self.is_processing = False
            self.log("Processing cancelled by user.", level="warning")
            self.process_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
    
    def update_progress(self, value: float, message: str = ""):
        """Update the progress bar and label."""
        # Ensure value is between 0 and 1
        value = max(0, min(1, value))
        percentage = int(value * 100)
        
        # Update UI elements
        self.progress_var.set(value)
        self.progress_bar.set(value)
        
        if message:
            self.progress_label.configure(text=f"{percentage}% - {message}")
        else:
            self.progress_label.configure(text=f"{percentage}%")
        
        # Update UI
        self.root.update_idletasks()
    
    def process_image(self):
        """Process the image to create color variations."""
        try:
            self.log("Starting image processing...", level="info")
            
            # Get processing parameters
            saturation_levels = self.saturation_value.get()
            hue_variations = self.hue_value.get()
            
            if saturation_levels <= 0:
                self.log("Saturation levels must be greater than 0. Using default (3).", level="warning")
                saturation_levels = 3
            
            if hue_variations <= 0:
                self.log("Hue variations must be greater than 0. Using default (10).", level="warning")
                hue_variations = 10
            
            # Get RGB adjustment values
            red_factor = self.red_value.get() / 100.0
            green_factor = self.green_value.get() / 100.0
            blue_factor = self.blue_value.get() / 100.0
            
            # Get grayscale-skip mode
            grayscale_mode = self.grayscale_mode.get()
            threshold = self.threshold_value.get()
            
            # Get transparency mode
            transparency_mode = self.transparency_mode.get()
            
            # Get output directory and create if needed
            output_dir = self.output_dir_var.get()
            if not output_dir:
                output_dir = os.path.dirname(self.input_image_path)
            
            prefix = self.prefix_value.get()
            if not prefix:
                prefix = "variation"
            
            # Get original filename (without extension)
            base_filename = os.path.splitext(os.path.basename(self.input_image_path))[0]
            
            # Create output directory with prefix
            output_subdir = f"{base_filename}_{prefix}"
            output_path = os.path.join(output_dir, output_subdir)
            
            # Handle case when directory already exists
            dir_index = 0
            original_output_path = output_path
            while os.path.exists(output_path):
                dir_index += 1
                output_path = f"{original_output_path}_{dir_index}"
            
            os.makedirs(output_path, exist_ok=True)
            self.log(f"Created output directory: {output_path}", level="info")
            
            # Create thumbnails directory
            thumbnails_dir = os.path.join(output_path, "thumbnails")
            os.makedirs(thumbnails_dir, exist_ok=True)
            
            # Calculate total number of variations
            total_variations = saturation_levels * hue_variations
            self.log(f"Generating {total_variations} variations ({saturation_levels} saturation × {hue_variations} hue)", level="info")
            
            # Process the image
            variations_created = 0
            thumbnail_paths = []
            
            # Load the image in OpenCV format if not already loaded
            if self.cv_image is None:
                # Reload the image
                if self.input_image.mode == 'RGBA':
                    self.cv_image = cv2.cvtColor(np.array(self.input_image), cv2.COLOR_RGBA2BGRA)
                else:
                    self.cv_image = cv2.cvtColor(np.array(self.input_image), cv2.COLOR_RGB2BGR)
            
            # Check if the image has an alpha channel
            has_alpha = len(self.cv_image.shape) == 3 and self.cv_image.shape[2] == 4
            
            # Start generating variations
            for sat_idx in range(saturation_levels):
                if not self.is_processing:
                    break
                
                # Calculate saturation factor (0% to 100%)
                sat_factor = (sat_idx + 1) / saturation_levels
                
                for hue_idx in range(hue_variations):
                    if not self.is_processing:
                        break
                    
                    # Calculate hue shift (0° to 360°)
                    hue_shift = (360.0 / hue_variations) * hue_idx
                    
                    # Update progress
                    variations_created += 1
                    progress = variations_created / total_variations
                    self.update_progress(progress, f"Processing variation {variations_created}/{total_variations}")
                    
                    # Process image based on whether it has alpha channel
                    if has_alpha:
                        # Process image with alpha channel
                        variation = self.process_rgba_image(
                            self.cv_image.copy(),
                            hue_shift,
                            sat_factor,
                            red_factor,
                            green_factor,
                            blue_factor,
                            grayscale_mode,
                            threshold,
                            transparency_mode
                        )
                    else:
                        # Process image without alpha channel
                        variation = self.process_rgb_image(
                            self.cv_image.copy(),
                            hue_shift,
                            sat_factor,
                            red_factor,
                            green_factor,
                            blue_factor,
                            grayscale_mode,
                            threshold
                        )
                    
                    # Save the variation
                    variation_filename = f"{base_filename}_{prefix}_{variations_created:02d}.png"
                    variation_path = os.path.join(output_path, variation_filename)
                    
                    cv2.imwrite(variation_path, variation)
                    self.log(f"Saved variation {variations_created}/{total_variations}: {variation_filename}", level="info")
                    
                    # Create and save thumbnail
                    thumbnail = self.create_thumbnail(variation)
                    thumbnail_filename = f"thumb_{variations_created:02d}.png"
                    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                    cv2.imwrite(thumbnail_path, thumbnail)
                    thumbnail_paths.append((thumbnail_path, variation_path))
            
            # Processing completed
            if self.is_processing:
                self.log(f"Processing completed: {variations_created} variations created", level="success")
                self.update_progress(1.0, "Done")
                
                # Show thumbnails preview if variations were created
                if variations_created > 0:
                    self.show_thumbnails_preview(thumbnail_paths, output_path)
            else:
                self.log("Processing cancelled", level="warning")
            
        except Exception as e:
            self.log(f"Error during processing: {str(e)}", level="error")
            import traceback
            traceback.print_exc()
        finally:
            # Reset UI state
            self.is_processing = False
            self.process_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
    
    def process_rgb_image(self, img, hue_shift, sat_factor, r_factor, g_factor, b_factor, 
                         grayscale_mode, threshold):
        """Process an RGB image to create a variation."""
        # Convert to HSV for easier manipulation of hue and saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # Apply hue shift and saturation adjustment
        h, s, v = cv2.split(hsv)
        
        # Shift hue (H is in range [0, 180] in OpenCV)
        h = np.mod(h + hue_shift / 2, 180).astype(np.float32)
        
        # Adjust saturation
        s = np.clip(s * sat_factor, 0, 255).astype(np.float32)
        
        # Handle grayscale pixels
        if grayscale_mode > 0:
            # Get original BGR channels
            b, g, r = cv2.split(img)
            
            if grayscale_mode == 1:  # Exact grayscale
                # Create a mask where R=G=B
                grayscale_mask = (r == g) & (g == b)
            else:  # Near grayscale
                # Create a mask where max(R,G,B) - min(R,G,B) < threshold
                min_rgb = np.minimum(np.minimum(r, g), b)
                max_rgb = np.maximum(np.maximum(r, g), b)
                grayscale_mask = (max_rgb - min_rgb) < threshold
            
            # Apply mask - don't change hue and saturation for grayscale pixels
            h = np.where(grayscale_mask, h, h)
            s = np.where(grayscale_mask, 0, s)  # Set saturation to 0 for grayscale pixels
        
        # Merge channels back
        hsv = cv2.merge([h, s, v])
        
        # Convert back to BGR
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # Apply RGB adjustments if saturation is low
        if sat_factor < 0.5:
            b, g, r = cv2.split(result)
            r = np.clip(r * r_factor, 0, 255).astype(np.uint8)
            g = np.clip(g * g_factor, 0, 255).astype(np.uint8)
            b = np.clip(b * b_factor, 0, 255).astype(np.uint8)
            result = cv2.merge([b, g, r])
        
        return result
    
    def process_rgba_image(self, img, hue_shift, sat_factor, r_factor, g_factor, b_factor, 
                          grayscale_mode, threshold, transparency_mode):
        """Process an RGBA image to create a variation."""
        # Split the image into BGR and Alpha channels
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
        
        # Create a processing mask based on transparency mode
        if transparency_mode == 0:
            # Process all pixels
            process_mask = np.ones(alpha.shape, dtype=bool)
        elif transparency_mode == 1:
            # Only process transparent pixels
            process_mask = alpha < 255
        else:
            # Only process non-transparent pixels
            process_mask = alpha == 255
        
        # Process the BGR channels
        processed_bgr = self.process_rgb_image(
            bgr, hue_shift, sat_factor, r_factor, g_factor, b_factor, grayscale_mode, threshold
        )
        
        # Create the final result by combining original and processed
        result_bgr = np.where(process_mask[:, :, np.newaxis], processed_bgr, bgr)
        
        # Combine with alpha channel
        result = cv2.merge([result_bgr[:, :, 0], result_bgr[:, :, 1], result_bgr[:, :, 2], alpha])
        
        return result
    
    def create_thumbnail(self, img, size=(100, 100)):
        """Create a thumbnail of the given image."""
        h, w = img.shape[:2]
        
        # Calculate aspect ratio
        aspect_ratio = w / h
        
        if aspect_ratio > 1:
            # Image is wider than tall
            new_w = size[0]
            new_h = int(new_w / aspect_ratio)
        else:
            # Image is taller than wide
            new_h = size[1]
            new_w = int(new_h * aspect_ratio)
        
        # Resize the image
        thumbnail = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # If the image has an alpha channel, make a white background
        if thumbnail.shape[2] == 4:
            # Create a white background
            background = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
            
            # Calculate position to center the image
            y_offset = (size[1] - new_h) // 2
            x_offset = (size[0] - new_w) // 2
            
            # Extract RGB and Alpha
            rgb = thumbnail[:, :, :3]
            alpha = thumbnail[:, :, 3].astype(float) / 255
            
            # For each channel, blend with the background
            for c in range(3):
                background[y_offset:y_offset+new_h, x_offset:x_offset+new_w, c] = (
                    rgb[:, :, c] * alpha + 
                    background[y_offset:y_offset+new_h, x_offset:x_offset+new_w, c] * (1 - alpha)
                ).astype(np.uint8)
            
            return background
        else:
            # For RGB images, just return the resized image
            return thumbnail
    
    def show_thumbnails_preview(self, thumbnail_paths, output_dir):
        """Show a window with thumbnails of all generated variations."""
        try:
            # Create a new window
            preview_window = ctk.CTkToplevel(self.root)
            preview_window.title("Generated Variations Preview")
            preview_window.geometry("800x600")
            preview_window.minsize(600, 400)
            
            # Add a label
            header_label = ctk.CTkLabel(
                preview_window, 
                text=f"Generated {len(thumbnail_paths)} Variations", 
                font=("Arial", 16, "bold")
            )
            header_label.pack(pady=10)
            
            # Add info about save location
            location_label = ctk.CTkLabel(
                preview_window,
                text=f"Saved to: {output_dir}",
                font=("Arial", 12)
            )
            location_label.pack(pady=(0, 10))
            
            # Create a scrollable frame for thumbnails
            container_frame = ctk.CTkFrame(preview_window)
            container_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create canvas and scrollbar
            canvas = ctk.CTkCanvas(container_frame, bg="#2b2b2b", highlightthickness=0)
            scrollbar = ctk.CTkScrollbar(container_frame, orientation="vertical", command=canvas.yview)
            
            # Configure canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Create a frame inside canvas for thumbnails
            thumbnails_frame = ctk.CTkFrame(canvas)
            canvas.create_window((0, 0), window=thumbnails_frame, anchor="nw")
            
            # Thumbnail storage to prevent garbage collection
            self.thumbnail_images = []
            
            # Add thumbnails in a grid layout
            grid_columns = 5
            current_row = 0
            current_col = 0
            
            # Function to open an image
            def open_image(image_path):
                try:
                    # Use default system image viewer
                    if sys.platform == 'win32':
                        os.startfile(image_path)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{image_path}"')
                    else:
                        os.system(f'xdg-open "{image_path}"')
                except Exception as e:
                    self.log(f"Error opening image: {e}", level="error")
            
            # Add thumbnails
            for idx, (thumb_path, variation_path) in enumerate(thumbnail_paths):
                # Create frame for thumbnail
                thumb_frame = ctk.CTkFrame(thumbnails_frame, width=120, height=140)
                thumb_frame.grid(row=current_row, column=current_col, padx=5, pady=5)
                thumb_frame.grid_propagate(False)  # Prevent shrinking
                
                # Load thumbnail image
                pil_img = Image.open(thumb_path)
                thumb_img = ImageTk.PhotoImage(pil_img)
                self.thumbnail_images.append(thumb_img)  # Keep reference to prevent GC
                
                # Create image label
                img_label = ctk.CTkLabel(thumb_frame, image=thumb_img, text="")
                img_label.pack(pady=(5, 0))
                
                # Add caption label
                caption = f"Variation {idx+1:02d}"
                caption_label = ctk.CTkLabel(thumb_frame, text=caption, font=("Arial", 10))
                caption_label.pack(pady=(0, 5))
                
                # Make clickable to open the original image
                img_label.bind("<Button-1>", lambda e, path=variation_path: open_image(path))
                
                # Update grid position
                current_col += 1
                if current_col >= grid_columns:
                    current_col = 0
                    current_row += 1
            
            # Update the canvas scroll region
            thumbnails_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))
            
            # Add a button to close the window
            close_button = ctk.CTkButton(
                preview_window, 
                text="Close Preview", 
                command=preview_window.destroy
            )
            close_button.pack(pady=10)
            
            # Add a button to open the output folder
            def open_output_folder():
                try:
                    if sys.platform == 'win32':
                        os.startfile(output_dir)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{output_dir}"')
                    else:
                        os.system(f'xdg-open "{output_dir}"')
                except Exception as e:
                    self.log(f"Error opening folder: {e}", level="error")
            
            open_folder_button = ctk.CTkButton(
                preview_window, 
                text="Open Output Folder", 
                command=open_output_folder
            )
            open_folder_button.pack(pady=(0, 10))
            
        except Exception as e:
            self.log(f"Error displaying thumbnails: {e}", level="error")
    
    def on_window_resize(self, event=None):
        """Handle window resize event to update the preview."""
        if hasattr(self, 'preview_canvas') and self.input_image is not None:
            # Update the preview when window is resized
            self.update_preview()
    
    def update_config(self):
        """Update the configuration with current settings."""
        self.config = {
            "saturation_levels": self.saturation_value.get(),
            "hue_variations": self.hue_value.get(),
            "red_value": self.red_value.get(),
            "green_value": self.green_value.get(),
            "blue_value": self.blue_value.get(),
            "grayscale_mode": self.grayscale_mode.get(),
            "threshold": self.threshold_value.get(),
            "transparency_mode": self.transparency_mode.get(),
            "output_dir": self.output_dir_var.get(),
            "prefix": self.prefix_value.get()
        }
        
        # Save to file
        self.save_config()
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "saturation_levels": 3,
                    "hue_variations": 10,
                    "red_value": 100,
                    "green_value": 100,
                    "blue_value": 100,
                    "grayscale_mode": 0,
                    "threshold": 10,
                    "transparency_mode": 0,
                    "output_dir": "",
                    "prefix": "variation"
                }
        except Exception:
            # If there's an error loading config, use defaults
            self.config = {
                "saturation_levels": 3,
                "hue_variations": 10,
                "red_value": 100,
                "green_value": 100,
                "blue_value": 100,
                "grayscale_mode": 0,
                "threshold": 10,
                "transparency_mode": 0,
                "output_dir": "",
                "prefix": "variation"
            }
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def on_closing(self):
        """Handle window closing event."""
        # Stop any ongoing processing
        self.is_processing = False
        
        # Save current settings
        self.update_config()
        
        # Close the window
        self.root.destroy()

def main():
    # Create the Tkinter root window
    root = ctk.CTk()
    
    # Create the application
    app = ColorVariationGenerator(root)
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()