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
import shutil

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
# Windowsの標準フォントを設定
DEFAULT_FONT = ("Meiryo UI", 12, "bold")
HEADING_FONT = ("Meiryo UI", 14, "bold")

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

def adjust_image_rgb(image, r_strength=1.0, g_strength=1.0, b_strength=1.0, mode="additive"):
    """B channels of an image using a specified method.
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

    def create_ui(self):
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Split into left (image preview) and right (controls) sections
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5) # Refactored padding
        
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side="right", fill="y", padx=5, pady=5, ipadx=5) # Refactored padding
        
        # Image preview area
        self.preview_frame = ctk.CTkFrame(self.left_frame)
        self.preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="ここに画像をドロップ", font=DEFAULT_FONT)
        self.preview_label.pack(fill="both", expand=True)
        
        # RGB sliders section
        self.control_frame = ctk.CTkFrame(self.right_frame)
        self.control_frame.pack(fill="x", padx=5, pady=5) # Refactored padding
        
        self.rgb_label = ctk.CTkLabel(self.control_frame, text="RGB調整", font=HEADING_FONT)
        self.rgb_label.pack(pady=(5, 0))
        
        # RGB Adjustment Mode Selector
        self.rgb_mode_frame = ctk.CTkFrame(self.control_frame)
        self.rgb_mode_frame.pack(fill="x", pady=(5,5))
        
        self.rgb_mode_label = ctk.CTkLabel(self.rgb_mode_frame, text="調整モード:", font=DEFAULT_FONT)
        self.rgb_mode_label.pack(side="left", padx=(5,5))

        self.rgb_mode_selector = ctk.CTkSegmentedButton(
            self.rgb_mode_frame, 
            values=["Additive", "Multiplicative"],
            variable=self.rgb_adjustment_mode,
            command=self.update_preview # Update preview when mode changes
        )
        self.rgb_mode_selector.pack(side="left", padx=2, expand=True, fill="x")
        
        # Red slider and entry
        self.r_frame = ctk.CTkFrame(self.control_frame)
        self.r_frame.pack(fill="x", pady=5)
        
        self.r_label = ctk.CTkLabel(self.r_frame, text="R:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.r_label.pack(side="left", padx=(5,2))
        
        self.r_slider = ctk.CTkSlider(self.r_frame, from_=0.0, to=2.0, variable=self.r_value, 
                                     command=self.update_preview)
        self.r_slider.pack(side="left", fill="x", expand=True, padx=2)
        
        # display the value of the r_value. this is no entry, just a label
        self.r_display.set(f"{self.r_value.get():.1f}")
        self.r_display_label = ctk.CTkLabel(self.r_frame, textvariable=self.r_display, width=40, font=DEFAULT_FONT)
        self.r_display_label.pack(side="left", padx=(2,5))

        # Green slider and entry
        self.g_frame = ctk.CTkFrame(self.control_frame)
        self.g_frame.pack(fill="x", pady=5)
        
        self.g_label = ctk.CTkLabel(self.g_frame, text="G:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.g_label.pack(side="left", padx=(5,2))
        
        self.g_slider = ctk.CTkSlider(self.g_frame, from_=0.0, to=2.0, variable=self.g_value,
                                     command=self.update_preview)
        self.g_slider.pack(side="left", fill="x", expand=True, padx=2)

        # display the value of the g_value. this is no entry, just a label
        self.g_display.set(f"{self.g_value.get():.1f}")
        self.g_display_label = ctk.CTkLabel(self.g_frame, textvariable=self.g_display, width=40, font=DEFAULT_FONT)
        self.g_display_label.pack(side="left", padx=(2,5))
        
        # Blue slider and entry
        self.b_frame = ctk.CTkFrame(self.control_frame)
        self.b_frame.pack(fill="x", pady=5)
        
        self.b_label = ctk.CTkLabel(self.b_frame, text="B:", width=15, font=DEFAULT_FONT) # Adjusted width
        self.b_label.pack(side="left", padx=(5,2))
        
        self.b_slider = ctk.CTkSlider(self.b_frame, from_=0.0, to=2.0, variable=self.b_value,
                                     command=self.update_preview)
        self.b_slider.pack(side="left", fill="x", expand=True, padx=2)

        # display the value of the b_value. this is no entry, just a label
        self.b_display.set(f"{self.b_value.get():.1f}")
        self.b_display_label = ctk.CTkLabel(self.b_frame, textvariable=self.b_display, width=40, font=DEFAULT_FONT)
        self.b_display_label.pack(side="left", padx=(2,5))
        
        # Variation settings
        self.var_frame = ctk.CTkFrame(self.right_frame)
        self.var_frame.pack(fill="x", padx=5, pady=5) # Refactored padding
        
        self.var_label = ctk.CTkLabel(self.var_frame, text="バリエーション設定", font=HEADING_FONT)
        self.var_label.pack(pady=(5, 0)) # TEST: padding
        
        # Hue variations
        self.hue_frame = ctk.CTkFrame(self.var_frame)
        self.hue_frame.pack(fill="x", pady=5)
        
        self.hue_label = ctk.CTkLabel(self.hue_frame, text="色相バリエーション:", width=100, font=DEFAULT_FONT)
        self.hue_label.pack(side="left", padx=5)
        
        self.hue_entry = ctk.CTkEntry(self.hue_frame, textvariable=self.hue_var_count, width=50, font=DEFAULT_FONT)
        self.hue_entry.pack(side="right", padx=5)
        
        # Saturation variations
        self.sat_frame = ctk.CTkFrame(self.var_frame)
        self.sat_frame.pack(fill="x", pady=5)
        
        self.sat_label = ctk.CTkLabel(self.sat_frame, text="彩度バリエーション:", width=100, font=DEFAULT_FONT) # Adjusted width
        self.sat_label.pack(side="left", padx=5)
        
        self.sat_entry = ctk.CTkEntry(self.sat_frame, textvariable=self.sat_var_count, width=50, font=DEFAULT_FONT)
        self.sat_entry.pack(side="right", padx=5)
        
        # Output path settings
        self.output_frame = ctk.CTkFrame(self.right_frame)
        self.output_frame.pack(fill="x", padx=5, pady=5) # Refactored padding
        
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
        
        self.generate_button = ctk.CTkButton(
            self.button_frame,
            text="バリエーション生成",  # 強調のために★を追加
            command=self.generate_variations,
            state="disabled",
            font=("Meiryo UI", 14, "bold"),  # 太字で強調
            fg_color="#FF8800",   # オレンジ色
            text_color="#FFFFFF",  # 白文字
            text_color_disabled="#FFFFFF",  # 無効時も白文字
        )
        self.generate_button.pack(fill="x", padx=5, pady=2)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.right_frame,
            orientation="horizontal",
            mode="determinate",
            progress_color="#4CAF50"  # 緑色 (Material Green 500)
        )
        self.progress_bar.pack(fill="x", padx=5, pady=(5,10))
        self.progress_bar.set(0)

        # Log area
        self.log_frame = ctk.CTkFrame(self.right_frame)
        self.log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="ログ", font=HEADING_FONT)
        self.log_label.pack(pady=(5, 0))
        
        self.log_text = ctk.CTkTextbox(self.log_frame, height=50, font=DEFAULT_FONT) # Adjusted height
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # リセットボタンをログ表示の下に移動
        self.reset_button = ctk.CTkButton(self.right_frame, text="設定をリセット", command=self.reset_settings, font=DEFAULT_FONT)
        self.reset_button.pack(fill="x", padx=5, pady=5)

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
        if not self._validate_image():
            return
            
        try:
            output_path = self._prepare_output_path()
            hue_count = self.hue_var_count.get()
            sat_count = self.sat_var_count.get()
            
            self._start_generation_thread(output_path, hue_count, sat_count)
            
        except Exception as e:
            self.log(f"エラー: {str(e)}")
            traceback.print_exc()

    def _validate_image(self):
        """Validate that image is loaded"""
        if not self.adjusted_image:
            self.log("エラー: 画像が読み込まれていません")
            return False
        return True

    def _prepare_output_path(self):
        """Prepare and return the output path"""
        output_path = self.output_path_var.get()
        if output_path == "Default (input directory)":
            self.update_default_output_path()
            output_path = self.output_path_var.get()
        return output_path

    def _start_generation_thread(self, output_path, hue_count, sat_count):
        """Start the generation process in a separate thread"""
        thread = threading.Thread(
            target=self._generate_variations_thread, 
            args=(output_path, hue_count, sat_count)
        )
        thread.daemon = True
        thread.start()
        self.log(f"バリエーション生成を開始しました: {output_path}")

    def _generate_variations_thread(self, output_path, hue_count, sat_count):
        """Thread function to generate variations without freezing UI"""
        try:
            output_path = self._setup_output_directories(output_path)
            combined_dir = output_path
            
            variations = self._generate_combined_variations(hue_count, sat_count)
            self._save_variations(variations, combined_dir, output_path)
            
        except Exception as e:
            self._handle_generation_error(e)
        finally:
            self._cleanup_progress_bar()

    def _setup_output_directories(self, output_path):
        """Setup output directories and return final output path"""
        if not self.overwrite_var.get():
            output_path = get_unique_folder_path(output_path)
            
        os.makedirs(output_path, exist_ok=True)
        
        return output_path

    def _generate_combined_variations(self, hue_count, sat_count):
        """Generate all hue/saturation combinations"""
        self.log(f"組み合わせバリエーションを生成中 (合計 {hue_count * sat_count})...")
        self.progress_bar.configure(mode="determinate")
        
        variations = []
        total_variations = hue_count * sat_count
        generated_count = 0
        
        has_alpha = self.adjusted_image.mode == 'RGBA'
        image_np = np.array(self.adjusted_image)

        for h_idx in range(hue_count):
            hue = h_idx * (180 / hue_count)
            hue_display = hue * 2
            hue_label = f"{int(hue_display)}°"
            
            for s_idx in range(sat_count):
                saturation = (s_idx + 1) * (1 / sat_count)
                sat_label = f"{int(saturation * 100)}%"
                
                variation = self._create_single_variation(
                    image_np, hue, saturation, hue_label, sat_label, has_alpha
                )
                variations.append(variation)
                
                generated_count += 1
                progress = generated_count / (total_variations * 2)
                self.after(0, lambda p=progress: self.progress_bar.set(p))
        
        return variations

    def _create_single_variation(self, image_np, hue, saturation, hue_label, sat_label, has_alpha):
        """Create a single hue/saturation variation"""
        if has_alpha:
            return self._create_alpha_variation(image_np, hue, saturation, hue_label, sat_label)
        else:
            return self._create_rgb_variation(image_np, hue, saturation, hue_label, sat_label)

    def _create_alpha_variation(self, image_np, hue, saturation, hue_label, sat_label):
        """Create variation for RGBA image"""
        rgb_channels = image_np[:, :, :3]
        alpha_channel = image_np[:, :, 3]
        hsv_image = cv2.cvtColor(rgb_channels, cv2.COLOR_RGB2HSV)
        hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
        hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
        rgb_result = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
        
        result = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
        result[:, :, :3] = rgb_result
        result[:, :, 3] = alpha_channel
        
        return {
            'image': Image.fromarray(result, 'RGBA'),
            'hue': hue_label,
            'saturation': sat_label
        }

    def _create_rgb_variation(self, image_np, hue, saturation, hue_label, sat_label):
        """Create variation for RGB image"""
        hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
        hsv_image[:, :, 0] = (hsv_image[:, :, 0] + hue) % 180
        hsv_image[:, :, 1] = hsv_image[:, :, 1] * saturation
        color_variation = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)
        
        return {
            'image': Image.fromarray(color_variation),
            'hue': hue_label,
            'saturation': sat_label
        }

    def _save_variations(self, variations, combined_dir, output_path):
        """Save all variations to disk"""
        self.log("バリエーションデータの生成完了。保存を開始します...")
        
        original_filename = os.path.splitext(os.path.basename(self.image_path))[0]
        
        # Save variations
        for i, var in enumerate(variations):
            filename = f"{original_filename}_{i:03d}.png"
            filename = filename.replace("°", "deg").replace("%", "pct")
            filepath = os.path.join(combined_dir, filename)
            
            if var['image'].mode == 'RGBA':
                var['image'].save(filepath, format="PNG")
            else:
                var['image'].save(filepath)

            # progress update
            progress = (i + 1) / (len(variations) * 2) + 0.5
            self.after(0, lambda p=progress: self.progress_bar.set(p))
        
        self._log_save_success(len(variations), combined_dir, output_path)

    def _save_adjusted_original(self, output_path, original_filename):
        """Save the adjusted original image"""
        filepath = os.path.join(output_path, f"{original_filename}_adjusted.png")
        if self.adjusted_image.mode == 'RGBA':
            self.adjusted_image.save(filepath, format="PNG")
        else:
            self.adjusted_image.save(filepath)

    def _log_save_success(self, variation_count, combined_dir, output_path):
        """Log successful save operation"""
        self.progress_bar.set(1.0)
        self.log(f"バリエーションの保存に成功しました:")
        self.log(f"- {variation_count}個の組み合わせバリエーション: {combined_dir}")
        self.log(f"- 調整済み元画像: {output_path}")

    def _handle_generation_error(self, error):
        """Handle errors during generation"""
        self.log(f"バリエーション生成エラー: {str(error)}")
        traceback.print_exc()
        self.progress_bar.set(0)

    def _cleanup_progress_bar(self):
        """Clean up progress bar after generation"""
        self.progress_bar.stop()
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
    else:
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



