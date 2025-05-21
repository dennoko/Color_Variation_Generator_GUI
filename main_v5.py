import os
import threading
import traceback
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import cv2
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import sys

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
# Windowsの標準フォントを設定
DEFAULT_FONT = ("Meiryo UI", 10)
HEADING_FONT = ("Meiryo UI", 12, "bold")

def load_image(image_path):
    """
    Load an image from a given path with error handling.
    
    Args:
        image_path (str): The path to the image.
    Returns:
        image (PIL.Image): The loaded image.
    Raises:
        Exception: If the image cannot be loaded.
    """
    try:
        image = Image.open(image_path)
        return image
    except Exception as e:
        raise Exception(f"Failed to load image: {str(e)}")

def generate_hue_variations(image, num_variations=5):
    """
    Generate hue variations of an image with error handling.
    
    Args:
        image (PIL.Image): The input image.
        num_variations (int): The number of color variations to generate.
    Returns:
        variations (list): A list of color variations.
    """
    try:
        if num_variations < 1:
            raise ValueError("Number of variations must be at least 1")
            
        # Convert the image to a NumPy array
        image_np = np.array(image)
        variations = []

        for i in range(num_variations):
            # OpenCV uses hue range 0-179 (not 0-359), so scale appropriately
            hue = i * (180 / num_variations)
            
            # Convert the image to HSV color space
            hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
            # Apply the hue transformation
            hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
            # Convert back to RGB
            color_variation = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
            variations.append(Image.fromarray(color_variation))
            
        return variations
    except Exception as e:
        raise Exception(f"Failed to generate hue variations: {str(e)}")

def generate_saturation_variations(image, num_variations=5):
    """
    Generate saturation variations of an image with error handling.
    
    Args:
        image (PIL.Image): The input image.
        num_variations (int): The number of saturation variations to generate.
    Returns:
        variations (list): A list of saturation variations.
    """
    try:
        if num_variations < 1:
            raise ValueError("Number of variations must be at least 1")
            
        # Convert the image to a NumPy array
        image_np = np.array(image)
        variations = []

        for i in range(num_variations):
            saturation = (i + 1) * (1 / num_variations)
            
            # Convert the image to HSV color space
            hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
            # Apply the saturation transformation
            hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
            # Convert back to RGB
            color_variation = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
            variations.append(Image.fromarray(color_variation))
            
        return variations
    except Exception as e:
        raise Exception(f"Failed to generate saturation variations: {str(e)}")

def generate_combined_variations(image, hue_variations=5, sat_variations=5):
    """
    Generate all combinations of hue and saturation variations.
    Preserves transparency for images with alpha channel.
    
    Args:
        image (PIL.Image): The input image.
        hue_variations (int): The number of hue variations.
        sat_variations (int): The number of saturation variations.
    Returns:
        combined_variations (list): A list of [variation_image, hue_value, sat_value].
    """
    try:
        if hue_variations < 1 or sat_variations < 1:
            raise ValueError("Number of variations must be at least 1")
        
        # Check if image has alpha channel
        has_alpha = image.mode == 'RGBA'
        
        # Convert the image to a NumPy array
        image_np = np.array(image)
        combined_variations = []
        
        for h_idx in range(hue_variations):
            # OpenCV uses hue range 0-179 (not 0-359), so scale appropriately
            hue = h_idx * (180 / hue_variations)
            # For display labels, use conventional 0-360 range
            hue_display = hue * 2
            hue_label = f"{int(hue_display)}°"
            
            for s_idx in range(sat_variations):
                saturation = (s_idx + 1) * (1 / sat_variations)
                sat_label = f"{int(saturation * 100)}%"
                
                if has_alpha:
                    # Separate RGB and alpha channels
                    rgb_channels = image_np[:, :, :3]
                    alpha_channel = image_np[:, :, 3]
                    
                    # Convert RGB to HSV
                    hsv_image = cv2.cvtColor(rgb_channels, cv2.COLOR_RGB2HSV)
                    
                    # Apply hue transformation
                    hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
                    
                    # Apply saturation transformation
                    hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
                    
                    # Convert back to RGB
                    rgb_result = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
                    
                    # Recombine with alpha channel
                    result = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
                    result[:, :, :3] = rgb_result
                    result[:, :, 3] = alpha_channel
                    
                    # Store the variation with its parameters
                    combined_variations.append({
                        'image': Image.fromarray(result, 'RGBA'),
                        'hue': hue_label,
                        'saturation': sat_label
                    })
                else:
                    # For non-transparent images, use original method
                    hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
                    hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
                    hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
                    color_variation = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
                    
                    combined_variations.append({
                        'image': Image.fromarray(color_variation),
                        'hue': hue_label,
                        'saturation': sat_label
                    })
        
        return combined_variations
    except Exception as e:
        raise Exception(f"Failed to generate combined variations: {str(e)}")

def adjust_image_rgb(image, r_strength=1.0, g_strength=1.0, b_strength=1.0, mode="additive"):
    """
    Adjust the RGB channels of an image using a specified method.
    Preserves transparency for images with alpha channel.
    Strength values from 0.0 to 2.0.
    Mode can be "additive" or "multiplicative".
    
    Args:
        image (PIL.Image): The input image.
        r_strength (float): The strength of the red channel adjustment (0.0 to 2.0).
        g_strength (float): The strength of the green channel adjustment (0.0 to 2.0).
        b_strength (float): The strength of the blue channel adjustment (0.0 to 2.0).
        mode (str): The adjustment mode: "additive" or "multiplicative".
    Returns:
        PIL.Image: The adjusted image in RGBA format.
    """
    try:
        # Validate input parameters
        for channel, value in [("Red", r_strength), ("Green", g_strength), ("Blue", b_strength)]:
            if not 0.0 <= value <= 2.0:
                raise ValueError(f"{channel} strength must be between 0.0 and 2.0")
        
        # Ensure the image is in RGBA format for consistent processing
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
            
        image_np = np.array(image)
        
        # Separate RGB and alpha channels.
        # Convert RGB to float32 for calculations to prevent overflow/underflow and precision loss.
        rgb_channels_np_float = image_np[:, :, :3].astype(np.float32)
        alpha_channel_np = image_np[:, :, 3]  # Alpha channel remains uint8
            
        strengths = [r_strength, g_strength, b_strength]
        
        if mode.lower() == "additive":
            # MAX_ADJUSTMENT_FACTOR determines the scale of adjustment.
            # (strength - 1.0) ranges from -1.0 to +1.0.
            # Multiplying by 255.0 means adjustment can range from -255 to +255.
            MAX_ADJUSTMENT_FACTOR = 255.0 
            for i in range(3):  # Iterate R, G, B channels
                adjustment = (strengths[i] - 1.0) * MAX_ADJUSTMENT_FACTOR
                rgb_channels_np_float[:, :, i] += adjustment
        
        elif mode.lower() == "multiplicative":
            for i in range(3):  # Iterate R, G, B channels
                rgb_channels_np_float[:, :, i] *= strengths[i]
        
        else:
            raise ValueError(f"Unsupported adjustment mode: {mode}. Choose 'additive' or 'multiplicative'.")
            
        # Clip values to the valid 0-255 range and convert back to uint8
        adjusted_rgb_channels = np.clip(rgb_channels_np_float, 0, 255).astype(np.uint8)
            
        # Recombine with alpha channel. Create a new array for the result.
        result_np = np.zeros_like(image_np) # Use np.zeros_like to match shape and dtype
        result_np[:, :, :3] = adjusted_rgb_channels
        result_np[:, :, 3] = alpha_channel_np
            
        return Image.fromarray(result_np, 'RGBA')

    except Exception as e:
        # import traceback # Uncomment for detailed debugging
        # traceback.print_exc() # Uncomment for detailed debugging
        raise Exception(f"Failed to adjust image: {str(e)}")

def save_images(images, output_path, original_filename, prefix="variation"):
    """
    Save images to a given path with error handling.
    
    Args:
        images (list): The images to save.
        output_path (str): The path to save the images.
        original_filename (str): Original filename without extension.
        prefix (str): Prefix for image filenames.
    """
    try:
        os.makedirs(output_path, exist_ok=True)
        for i, image in enumerate(images):
            # Use original filename with sequential number
            image.save(f"{output_path}/{original_filename}_{prefix}_{i:03d}.png")
        return len(images)
    except Exception as e:
        raise Exception(f"Failed to save images: {str(e)}")

def save_combined_variations(variations, output_path, original_filename):
    """
    Save combined variations to a given path.
    
    Args:
        variations (list): List of dictionaries with image and parameters.
        output_path (str): The path to save the images.
        original_filename (str): Original filename without extension.
    """
    try:
        os.makedirs(output_path, exist_ok=True)
        for i, var in enumerate(variations):
            # Use original filename with hue and saturation values
            filename = f"{original_filename}_{i:03d}.png"
            # Replace special characters in filename
            filename = filename.replace("°", "deg").replace("%", "pct")
            
            # Explicitly ensure transparency is preserved by setting format based on mode
            if var['image'].mode == 'RGBA':
                var['image'].save(f"{output_path}/{filename}", format="PNG")
            else:
                var['image'].save(f"{output_path}/{filename}")
        return len(variations)
    except Exception as e:
        raise Exception(f"Failed to save combined variations: {str(e)}")

class ColorVariationApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        
        # ウィンドウアイコンを設定
        icon_path = "app_icon.ico"
        
        # PyInstallerでパッケージ化した場合のリソースパス対応
        if getattr(sys, 'frozen', False):
            # 実行ファイルの場所を基準にアイコンパスを設定
            base_path = sys._MEIPASS
            icon_path = os.path.join(base_path, "app_icon.ico")
        
        # アイコンファイルが存在する場合のみ設定
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # 以下、既存のコード
        # Set up the main window
        self.title("Color Variation Generator")
        self.geometry("1100x750") # Adjusted height for progress bar
        
        # Initialize variables
        self.image_path = None
        self.original_image = None
        self.adjusted_image = None
        self.r_value = ctk.DoubleVar(value=1.0)
        self.g_value = ctk.DoubleVar(value=1.0)
        self.b_value = ctk.DoubleVar(value=1.0)
        self.hue_var_count = ctk.IntVar(value=10)
        self.sat_var_count = ctk.IntVar(value=3)
        self.output_path_var = ctk.StringVar(value="Default (input directory)")
        self.rgb_adjustment_mode = ctk.StringVar(value="Additive") # Default to Additive
        self.overwrite_var = ctk.BooleanVar(value=False)  # Default: don't overwrite (append numbers)
        
        # Format variables for display
        self.r_display = ctk.StringVar(value="1.0")
        self.g_display = ctk.StringVar(value="1.0")
        self.b_display = ctk.StringVar(value="1.0")
        
        # Register callbacks to update display values
        self.r_value.trace_add("write", self.update_display_values)
        self.g_value.trace_add("write", self.update_display_values)
        self.b_value.trace_add("write", self.update_display_values)
        
        # Create the UI
        self.create_ui()
        
        # Set up drag and drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Initial log message
        self.log("アプリケーションが起動しました。画像をドラッグするか「Open Image」ボタンを使用してください。")
        
    def update_display_values(self, *args):
        """Update the formatted display values for RGB sliders"""
        self.r_display.set(f"{self.r_value.get():.1f}")
        self.g_display.set(f"{self.g_value.get():.1f}")
        self.b_display.set(f"{self.b_value.get():.1f}")

        # Update entry fields if they exist
        if hasattr(self, 'r_entry'):
            self.r_entry.delete(0, "end")
            self.r_entry.insert(0, f"{self.r_value.get():.1f}")
        if hasattr(self, 'g_entry'):
            self.g_entry.delete(0, "end")
            self.g_entry.insert(0, f"{self.g_value.get():.1f}")
        if hasattr(self, 'b_entry'):
            self.b_entry.delete(0, "end")
            self.b_entry.insert(0, f"{self.b_value.get():.1f}")

    def update_rgb_from_entry(self, *args):
        """Update RGB values from entry fields"""
        try:
            r = float(self.r_entry.get())
            if 0.0 <= r <= 2.0:
                self.r_value.set(r)
        except ValueError:
            pass # Ignore invalid input
        try:
            g = float(self.g_entry.get())
            if 0.0 <= g <= 2.0:
                self.g_value.set(g)
        except ValueError:
            pass # Ignore invalid input
        try:
            b = float(self.b_entry.get())
            if 0.0 <= b <= 2.0:
                self.b_value.set(b)
        except ValueError:
            pass # Ignore invalid input
        self.update_preview()
    
    def create_ui(self):
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Split into left (image preview) and right (controls) sections
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(5,2), pady=5) # Adjusted padding
        
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side="right", fill="y", padx=(2,5), pady=5, ipadx=5) # Adjusted padding
        
        # Image preview area
        self.preview_frame = ctk.CTkFrame(self.left_frame)
        self.preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="ここに画像をドロップ", font=DEFAULT_FONT)
        self.preview_label.pack(fill="both", expand=True)
        
        # RGB sliders section
        self.control_frame = ctk.CTkFrame(self.right_frame)
        self.control_frame.pack(fill="x", padx=2, pady=5) # Adjusted padding
        
        self.rgb_label = ctk.CTkLabel(self.control_frame, text="RGB調整", font=HEADING_FONT)
        self.rgb_label.pack(pady=(5, 0))
        
        # RGB Adjustment Mode Selector
        self.rgb_mode_frame = ctk.CTkFrame(self.control_frame)
        self.rgb_mode_frame.pack(fill="x", pady=(5,2))
        
        self.rgb_mode_label = ctk.CTkLabel(self.rgb_mode_frame, text="調整モード:", font=DEFAULT_FONT)
        self.rgb_mode_label.pack(side="left", padx=(5,2))

        self.rgb_mode_selector = ctk.CTkSegmentedButton(
            self.rgb_mode_frame, 
            values=["Additive", "Multiplicative"],
            variable=self.rgb_adjustment_mode,
            command=self.update_preview # Update preview when mode changes
        )
        self.rgb_mode_selector.pack(side="left", padx=2, expand=True, fill="x")
        
        # Red slider and entry
        self.r_frame = ctk.CTkFrame(self.control_frame)
        self.r_frame.pack(fill="x", pady=2)
        
        self.r_label = ctk.CTkLabel(self.r_frame, text="R:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.r_label.pack(side="left", padx=(5,2))
        
        self.r_slider = ctk.CTkSlider(self.r_frame, from_=0.0, to=2.0, variable=self.r_value, 
                                     command=self.update_preview)
        self.r_slider.pack(side="left", fill="x", expand=True, padx=2)
        
        self.r_entry = ctk.CTkEntry(self.r_frame, textvariable=self.r_display, width=40, font=DEFAULT_FONT)
        self.r_entry.pack(side="left", padx=(2,5))
        self.r_entry.bind("<Return>", self.update_rgb_from_entry)
        self.r_entry.bind("<FocusOut>", self.update_rgb_from_entry)

        # Green slider and entry
        self.g_frame = ctk.CTkFrame(self.control_frame)
        self.g_frame.pack(fill="x", pady=2)
        
        self.g_label = ctk.CTkLabel(self.g_frame, text="G:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.g_label.pack(side="left", padx=(5,2))
        
        self.g_slider = ctk.CTkSlider(self.g_frame, from_=0.0, to=2.0, variable=self.g_value,
                                     command=self.update_preview)
        self.g_slider.pack(side="left", fill="x", expand=True, padx=2)
        
        self.g_entry = ctk.CTkEntry(self.g_frame, textvariable=self.g_display, width=40, font=DEFAULT_FONT)
        self.g_entry.pack(side="left", padx=(2,5))
        self.g_entry.bind("<Return>", self.update_rgb_from_entry)
        self.g_entry.bind("<FocusOut>", self.update_rgb_from_entry)

        # Blue slider and entry
        self.b_frame = ctk.CTkFrame(self.control_frame)
        self.b_frame.pack(fill="x", pady=2)
        
        self.b_label = ctk.CTkLabel(self.b_frame, text="B:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.b_label.pack(side="left", padx=(5,2))
        
        self.b_slider = ctk.CTkSlider(self.b_frame, from_=0.0, to=2.0, variable=self.b_value,
                                     command=self.update_preview)
        self.b_slider.pack(side="left", fill="x", expand=True, padx=2)
        
        self.b_entry = ctk.CTkEntry(self.b_frame, textvariable=self.b_display, width=40, font=DEFAULT_FONT)
        self.b_entry.pack(side="left", padx=(2,5))
        self.b_entry.bind("<Return>", self.update_rgb_from_entry)
        self.b_entry.bind("<FocusOut>", self.update_rgb_from_entry)
        
        # Variation settings
        self.var_frame = ctk.CTkFrame(self.right_frame)
        self.var_frame.pack(fill="x", padx=2, pady=5) # Adjusted padding
        
        self.var_label = ctk.CTkLabel(self.var_frame, text="バリエーション設定", font=HEADING_FONT)
        self.var_label.pack(pady=(5, 0))
        
        # Hue variations
        self.hue_frame = ctk.CTkFrame(self.var_frame)
        self.hue_frame.pack(fill="x", pady=2)
        
        self.hue_label = ctk.CTkLabel(self.hue_frame, text="色相バリエーション:", width=100, font=DEFAULT_FONT)
        self.hue_label.pack(side="left", padx=5)
        
        self.hue_entry = ctk.CTkEntry(self.hue_frame, textvariable=self.hue_var_count, width=50, font=DEFAULT_FONT)
        self.hue_entry.pack(side="left", padx=5)
        
        # Saturation variations
        self.sat_frame = ctk.CTkFrame(self.var_frame)
        self.sat_frame.pack(fill="x", pady=2)
        
        self.sat_label = ctk.CTkLabel(self.sat_frame, text="彩度バリエーション:", width=120, font=DEFAULT_FONT) # Adjusted width
        self.sat_label.pack(side="left", padx=(5,2))
        
        self.sat_entry = ctk.CTkEntry(self.sat_frame, textvariable=self.sat_var_count, width=50, font=DEFAULT_FONT)
        self.sat_entry.pack(side="left", padx=(2,5))
        
        # Output path settings
        self.output_frame = ctk.CTkFrame(self.right_frame)
        self.output_frame.pack(fill="x", padx=2, pady=5) # Adjusted padding
        
        self.output_label = ctk.CTkLabel(self.output_frame, text="出力パス", font=HEADING_FONT)
        self.output_label.pack(pady=(5, 0))
        
        self.output_entry = ctk.CTkEntry(self.output_frame, textvariable=self.output_path_var, font=DEFAULT_FONT)
        self.output_entry.pack(fill="x", padx=5, pady=2)
        
        self.browse_button = ctk.CTkButton(self.output_frame, text="参照", command=self.browse_output, font=DEFAULT_FONT)
        self.browse_button.pack(fill="x", padx=5, pady=2)

        # Add overwrite checkbox
        self.overwrite_check = ctk.CTkCheckBox(self.output_frame, text="既存フォルダを上書きする", 
                                      variable=self.overwrite_var, font=DEFAULT_FONT)
        self.overwrite_check.pack(fill="x", padx=5, pady=2)
        
        # Action buttons
        self.button_frame = ctk.CTkFrame(self.right_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)
        
        self.open_button = ctk.CTkButton(self.button_frame, text="画像を開く", command=self.open_image, font=DEFAULT_FONT)
        self.open_button.pack(fill="x", padx=5, pady=2)
        
        self.generate_button = ctk.CTkButton(self.button_frame, text="バリエーション生成", 
                                           command=self.generate_variations, state="disabled", font=DEFAULT_FONT)
        self.generate_button.pack(fill="x", padx=5, pady=2)

        # Log area
        self.log_frame = ctk.CTkFrame(self.right_frame)
        self.log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="ログ", font=HEADING_FONT)
        self.log_label.pack(pady=(5, 0))
        
        self.log_text = ctk.CTkTextbox(self.log_frame, height=150, font=DEFAULT_FONT) # Adjusted height
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # リセットボタンをログ表示の下に移動
        self.reset_button = ctk.CTkButton(self.right_frame, text="設定をリセット", command=self.reset_settings, font=DEFAULT_FONT)
        self.reset_button.pack(fill="x", padx=5, pady=5)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.right_frame, orientation="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=(5,10))
        self.progress_bar.set(0)
    
    def reset_settings(self):
        """Reset all settings to their default values."""
        self.r_value.set(1.0)
        self.g_value.set(1.0)
        self.b_value.set(1.0)
        self.rgb_adjustment_mode.set("Additive")
        self.hue_var_count.set(10)
        self.sat_var_count.set(3)
        self.output_path_var.set("Default (input directory)")
        self.overwrite_var.set(False)  # Reset overwrite setting to default (false)
        if self.image_path:
            self.update_default_output_path()
        
        self.update_display_values() # Update display for RGB
        self.update_preview()
        self.log("設定がリセットされました。")

    def handle_drop(self, event):
        """Handle file drop events"""
        file_path = event.data
        # Clean up path (remove curly braces and quotes if present)
        file_path = file_path.strip('{}')
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        
        # Check if it's an image file
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in valid_extensions:
            self.load_image_file(file_path)
        else:
            self.log(f"エラー: サポートされていないファイル形式です。次のいずれかを使用してください: {', '.join(valid_extensions)}")
    
    def open_image(self):
        """Open file dialog to select an image"""
        file_path = ctk.filedialog.askopenfilename(
            title="画像を選択",
            filetypes=[
                ("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                ("すべてのファイル", "*.*")
            ]
        )
        if file_path:
            self.load_image_file(file_path)
    
    def load_image_file(self, file_path):
        """Load an image from the given path and update the preview"""
        try:
            self.log(f"画像を読み込み中: {file_path}")
            self.image_path = file_path
            self.original_image = load_image(file_path)
            
            # Update default output path
            self.update_default_output_path()
            
            # Update the image preview
            self.update_preview()
            
            # Enable the generate button
            self.generate_button.configure(state="normal")
            
            self.log(f"画像の読み込みに成功しました: {os.path.basename(file_path)}")
        except Exception as e:
            self.log(f"画像読み込みエラー: {str(e)}")
    
    def update_default_output_path(self):
        """Set default output path based on input image"""
        if self.image_path:
            input_dir = os.path.dirname(self.image_path)
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            default_output = os.path.join(input_dir, base_name)
            self.output_path_var.set(default_output)
    
    def update_preview(self, *args):
        """Update the image preview with current RGB adjustments, handling transparency"""
        if not self.original_image:
            return
        
        try:
            # Apply RGB adjustments
            self.adjusted_image = adjust_image_rgb(
                self.original_image,
                r_strength=self.r_value.get(),
                g_strength=self.g_value.get(),
                b_strength=self.b_value.get(),
                mode=self.rgb_adjustment_mode.get() # Pass selected mode
            )
            
            # Resize the image for preview (maintaining aspect ratio)
            preview_width = self.preview_frame.winfo_width() - 20
            preview_height = self.preview_frame.winfo_height() - 20
            
            if preview_width > 100 and preview_height > 100:
                img_width, img_height = self.adjusted_image.size
                
                # Calculate scaling factor
                scale_w = preview_width / img_width
                scale_h = preview_height / img_height
                scale = min(scale_w, scale_h)
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Resize and display
                display_img = self.adjusted_image.resize((new_width, new_height), Image.LANCZOS)
                
                # For transparent images, create a checkerboard background
                if display_img.mode == 'RGBA':
                    # Create a checkerboard pattern for transparency visualization
                    checkerboard = Image.new('RGB', display_img.size, (255, 255, 255))
                    
                    # Create checkerboard pattern
                    cell_size = 10  # Size of each checkerboard square
                    for y in range(0, display_img.height, cell_size):
                        for x in range(0, display_img.width, cell_size):
                            if (x // cell_size + y // cell_size) % 2 == 0:
                                box = (x, y, min(x + cell_size, display_img.width), 
                                      min(y + cell_size, display_img.height))
                                ImageDraw.Draw(checkerboard).rectangle(box, fill=(220, 220, 220))
                    
                    # より明示的な合成方法を使用
                    r, g, b, a = display_img.split()
                    # チェッカーボード上に色情報を貼り付け、アルファチャンネルをマスクとして使用
                    checkerboard.paste(Image.merge('RGB', (r, g, b)), (0, 0), a)
                    display_img = checkerboard
                
                photo = ImageTk.PhotoImage(display_img)
                
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo  # Keep a reference
        except Exception as e:
            self.log(f"プレビュー更新エラー: {str(e)}")
    
    def browse_output(self):
        """Open dialog to select output directory"""
        directory = ctk.filedialog.askdirectory(title="出力ディレクトリを選択")
        if directory:
            self.output_path_var.set(directory)
    
    def generate_variations(self):
        """Generate and save variations of the image"""
        if not self.adjusted_image:
            self.log("エラー: 画像が読み込まれていません")
            return
            
        try:
            # Get output path
            output_path = self.output_path_var.get()
            if output_path == "Default (input directory)":
                self.update_default_output_path()
                output_path = self.output_path_var.get()
                
            # Create output directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Get variation counts
            hue_count = self.hue_var_count.get()
            sat_count = self.sat_var_count.get()
            
            # Start generation in a separate thread to keep UI responsive
            thread = threading.Thread(
                target=self._generate_variations_thread, 
                args=(output_path, hue_count, sat_count)
            )
            thread.daemon = True
            thread.start()
            
            self.log(f"バリエーション生成を開始しました: {output_path}")
        except Exception as e:
            self.log(f"エラー: {str(e)}")
            traceback.print_exc()
    
    def _generate_variations_thread(self, output_path, hue_count, sat_count):
        """Thread function to generate variations without freezing UI"""
        try:
            self.progress_bar.set(0) # Reset progress bar
            self.progress_bar.start() # Indeterminate mode while preparing

            # Get original filename without extension
            original_filename = os.path.splitext(os.path.basename(self.image_path))[0]
            
            # Check if we need to create a unique path
            if not self.overwrite_var.get():
                output_path = get_unique_folder_path(output_path)
                
            # Define combined variations directory path
            combined_dir = os.path.join(output_path, "combined_variations")
            
            # Create output directories only once here
            os.makedirs(output_path, exist_ok=True)
            os.makedirs(combined_dir, exist_ok=True)
            
            self.log(f"組み合わせバリエーションを生成中 (合計 {hue_count * sat_count})...")
            
            # Temporarily switch to determinate mode for generation
            self.progress_bar.configure(mode="determinate")
            
            # --- Modified generate_combined_variations to yield progress ---
            # This requires modifying generate_combined_variations function
            # For simplicity, we'll update progress after the whole generation here.
            # A more granular progress would require deeper changes in generate_combined_variations.

            total_variations = hue_count * sat_count
            generated_count = 0

            # --- Simulate progress within this thread for now ---
            # In a real scenario, generate_combined_variations would need to be refactored
            # to report progress back, or we estimate progress based on loops.

            # For demonstration, let's assume generate_combined_variations is a black box
            # and we update progress after it's done with the main generation part.
            # A more accurate progress would involve modifying generate_combined_variations
            # to yield progress or accept a callback.

            combined_variations = []
            has_alpha = self.adjusted_image.mode == 'RGBA'
            image_np = np.array(self.adjusted_image)

            for h_idx in range(hue_count):
                hue = h_idx * (180 / hue_count)
                hue_display = hue * 2
                hue_label = f"{int(hue_display)}°"
                
                for s_idx in range(sat_count):
                    saturation = (s_idx + 1) * (1 / sat_count)
                    sat_label = f"{int(saturation * 100)}%"
                    
                    if has_alpha:
                        rgb_channels = image_np[:, :, :3]
                        alpha_channel = image_np[:, :, 3]
                        hsv_image = cv2.cvtColor(rgb_channels, cv2.COLOR_RGB2HSV)
                        hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
                        hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
                        rgb_result = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
                        result = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
                        result[:, :, :3] = rgb_result
                        result[:, :, 3] = alpha_channel
                        combined_variations.append({
                            'image': Image.fromarray(result, 'RGBA'),
                            'hue': hue_label,
                            'saturation': sat_label
                        })
                    else:
                        hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
                        hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
                        hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
                        color_variation = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
                        combined_variations.append({
                            'image': Image.fromarray(color_variation),
                            'hue': hue_label,
                            'saturation': sat_label
                        })
                    generated_count += 1
                    progress = generated_count / total_variations
                    self.after(0, lambda p=progress: self.progress_bar.set(p)) # Update progress bar in main thread
            # --- End of simulated progress section ---

            self.log("バリエーションデータの生成完了。保存を開始します...")
            self.progress_bar.set(0.8) # Example: 80% after generation, before saving
            
            # Save variations with original filename
            # For progress during saving, we'd iterate and update
            num_saved = 0
            for i, var in enumerate(combined_variations):
                filename = f"{original_filename}_{i:03d}.png"
                filename = filename.replace("°", "deg").replace("%", "pct")
                if var['image'].mode == 'RGBA':
                    var['image'].save(f"{combined_dir}/{filename}", format="PNG")
                else:
                    var['image'].save(f"{combined_dir}/{filename}")
                num_saved +=1
                # Update progress based on saved files (optional, can be slow if many small files)
                # save_progress = num_saved / len(combined_variations)
                # self.after(0, lambda p=0.8 + save_progress * 0.15: self.progress_bar.set(p))


            combined_saved = len(combined_variations) # Use actual count
            
            # Save original adjusted image with transparency preserved if present
            if self.adjusted_image.mode == 'RGBA':
                self.adjusted_image.save(f"{output_path}/{original_filename}_adjusted.png", format="PNG")
            else:
                self.adjusted_image.save(f"{output_path}/{original_filename}_adjusted.png")
            
            self.progress_bar.set(1.0) # Generation and saving complete
            self.log(f"バリエーションの保存に成功しました:")
            self.log(f"- {combined_saved}個の組み合わせバリエーション: {combined_dir}")
            self.log(f"- 調整済み元画像: {output_path}")
            
        except Exception as e:
            self.log(f"バリエーション生成エラー: {str(e)}")
            traceback.print_exc()
            self.progress_bar.set(0) # Reset on error
        finally:
            # Ensure progress bar stops indeterminate animation if it was running
            self.progress_bar.stop() 
            # Optionally hide or reset progress bar after a delay
            self.after(2000, lambda: self.progress_bar.set(0))


    def log(self, message):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Enable text widget for editing
        self.log_text.configure(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")  # Scroll to end
        self.log_text.configure(state="disabled")
        
        # Also print to console
        print(log_entry.strip())

def get_unique_folder_path(base_path):
    """
    Create a unique folder path by appending incrementing numbers if needed.
    
    Args:
        base_path (str): The base folder path to check
    Returns:
        str: A unique folder path (either the original or with a number appended)
    """
    if not os.path.exists(base_path):
        return base_path
        
    counter = 1
    while True:
        new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

# Main application entry point
if __name__ == "__main__":
    app = ColorVariationApp()
    app.mainloop()



