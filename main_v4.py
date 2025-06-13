#!/usr/bin/env python3
"""
Image Color Variations Generator

A command-line tool that processes an input image and generates multiple color variations
based on hue rotation and saturation scaling.
"""

import argparse
import cv2
import numpy as np
import os
import sys
from pathlib import Path
from PIL import Image
import json
import yaml
import logging
from tqdm import tqdm
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ImageProcessor:
    """Core image processing logic for generating color variations."""

    def __init__(self, config):
        """
        Initialize the image processor with configuration.
        
        Args:
            config (dict): Configuration parameters for image processing
        """
        self.config = config
        self.input_path = Path(config['input_path'])
        self.output_dir = Path(config['output_dir']) if config['output_dir'] else self.input_path.parent
        self.sat_count = config['saturation_count']
        self.hue_count = config['hue_count']
        self.r_scale = config['r_scale']
        self.g_scale = config['g_scale']
        self.b_scale = config['b_scale']
        self.skip_gray = config['skip_gray']
        self.skip_near_gray_threshold = config['skip_near_gray_threshold']
        self.transparent_only = config['transparent_only']
        self.opaque_only = config['opaque_only']
        self.verbose = config['verbose']
        self.dry_run = config['dry_run']
        self.log_file = config.get('log_file', None)
        
        # Set up logging to file if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
    
    def load_image(self):
        """
        Load image using Pillow for compatibility with non-ASCII paths, 
        then convert to OpenCV format.
        
        Returns:
            numpy.ndarray: The loaded image in OpenCV/NumPy format
        """
        try:
            # Use Pillow to load the image to handle non-ASCII paths
            pil_image = Image.open(self.input_path)
            
            # Convert PIL image to numpy array for OpenCV processing
            # Convert to RGB if it's not already
            if pil_image.mode == 'RGBA':
                # Image with alpha channel
                self.has_alpha = True
                img_array = np.array(pil_image)
                # OpenCV uses BGR order, but we'll work in RGB and convert as needed
                self.image = img_array
            elif pil_image.mode == 'RGB':
                # No alpha channel
                self.has_alpha = False
                img_array = np.array(pil_image)
                self.image = img_array
            else:
                # Convert to RGB or RGBA
                pil_image = pil_image.convert('RGB')
                self.has_alpha = False
                img_array = np.array(pil_image)
                self.image = img_array
                
            logger.info(f"Loaded image: {self.input_path} - Shape: {self.image.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load image {self.input_path}: {e}")
            return False
    
    def create_output_directory(self):
        """
        Create output directory with incrementing suffix if it already exists.
        
        Returns:
            Path: Path object representing the output directory
        """
        # If output directory doesn't exist, create it
        if not self.output_dir.exists():
            if not self.dry_run:
                self.output_dir.mkdir(parents=True)
            logger.info(f"Created output directory: {self.output_dir}")
            return self.output_dir
            
        # Create a specific folder for this batch
        base_name = self.input_path.stem
        batch_dir = self.output_dir / f"{base_name}_variations"
        
        # If the batch directory exists, add incremental suffix
        if batch_dir.exists():
            i = 1
            while (self.output_dir / f"{base_name}_variations_{i:02d}").exists():
                i += 1
            batch_dir = self.output_dir / f"{base_name}_variations_{i:02d}"
        
        if not self.dry_run:
            batch_dir.mkdir(parents=True)
        
        logger.info(f"Created batch directory: {batch_dir}")
        return batch_dir
    
    def process_image(self):
        """
        Process the image to generate variations based on hue and saturation.
        
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.load_image():
            return False
        
        if self.dry_run:
            logger.info("DRY RUN: Would process image and generate variations")
            self._simulate_dry_run()
            return True
        
        # Create output directory
        output_dir = self.create_output_directory()
        
        # Generate variations
        variations_count = self.sat_count * self.hue_count
        
        logger.info(f"Generating {variations_count} variations...")
        
        # Set up progress tracking
        if self.verbose:
            variations_iterator = tqdm(
                range(variations_count),
                desc="Processing variations",
                unit="image"
            )
        else:
            variations_iterator = range(variations_count)
        
        var_index = 0
        for sat_idx in range(self.sat_count):
            # Calculate saturation factor
            # Scale from 1/sat_count to 1.0
            sat_factor = (sat_idx + 1) / self.sat_count
            
            for hue_idx in range(self.hue_count):
                # Calculate hue rotation in degrees
                hue_rotation = (hue_idx * 360) / self.hue_count
                
                # Process image with current parameters
                output_img = self._apply_color_variation(sat_factor, hue_rotation)
                
                # Save the processed image
                output_filename = f"{self.input_path.stem}_variation_{var_index:02d}.png"
                output_path = output_dir / output_filename
                
                # Convert back to BGR for OpenCV saving
                if self.has_alpha:
                    # Save with alpha channel
                    cv2.imwrite(str(output_path), cv2.cvtColor(output_img, cv2.COLOR_RGBA2BGRA))
                else:
                    cv2.imwrite(str(output_path), cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR))
                
                if self.verbose:
                    logger.info(f"Saved variation {var_index+1}/{variations_count}: {output_path}")
                
                var_index += 1
                
                # Update progress bar
                if self.verbose:
                    variations_iterator.update(1)
        
        # Close progress bar
        if self.verbose and isinstance(variations_iterator, tqdm):
            variations_iterator.close()
        
        # Save processing details to log file
        self._save_processing_details(output_dir)
        
        logger.info(f"Processing complete. Variations saved to: {output_dir}")
        return True
    
    def _apply_color_variation(self, sat_factor, hue_rotation):
        """
        Apply color variation to the image based on saturation factor and hue rotation.
        
        Args:
            sat_factor (float): Saturation scaling factor (0.0 to 1.0)
            hue_rotation (float): Hue rotation in degrees (0 to 360)
            
        Returns:
            numpy.ndarray: Processed image
        """
        # Make a copy of the original image
        img_copy = self.image.copy()
        
        # Split the image into color channels + alpha if present
        if self.has_alpha:
            r_channel, g_channel, b_channel, alpha_channel = cv2.split(img_copy)
        else:
            r_channel, g_channel, b_channel = cv2.split(img_copy)
        
        # Create mask for pixels to process
        mask = np.ones_like(r_channel, dtype=bool)
        
        # Apply skip grayscale rules if enabled
        if self.skip_gray or self.skip_near_gray_threshold > 0:
            max_values = np.maximum.reduce([r_channel, g_channel, b_channel])
            min_values = np.minimum.reduce([r_channel, g_channel, b_channel])
            diff = max_values - min_values
            
            if self.skip_gray:
                # Exact grayscale pixels where R=G=B
                mask = mask & (diff > 0)
            
            if self.skip_near_gray_threshold > 0:
                # Near grayscale pixels
                mask = mask & (diff >= self.skip_near_gray_threshold)
        
        # Apply transparency rules if the image has an alpha channel
        if self.has_alpha:
            if self.transparent_only:
                # Process only fully or partially transparent pixels
                mask = mask & (alpha_channel < 255)
            elif self.opaque_only:
                # Process only fully opaque pixels
                mask = mask & (alpha_channel == 255)
        
        # Convert to HSV color space for easier manipulation of hue and saturation
        # We'll work on pixels that pass the mask
        for i in range(img_copy.shape[0]):
            for j in range(img_copy.shape[1]):
                if not mask[i, j]:
                    continue
                
                r, g, b = img_copy[i, j][:3]
                
                # Convert RGB to HSV
                r, g, b = r/255.0, g/255.0, b/255.0
                cmax = max(r, g, b)
                cmin = min(r, g, b)
                delta = cmax - cmin
                
                # Calculate hue
                h = 0
                if delta == 0:
                    h = 0
                elif cmax == r:
                    h = 60 * (((g - b) / delta) % 6)
                elif cmax == g:
                    h = 60 * ((b - r) / delta + 2)
                elif cmax == b:
                    h = 60 * ((r - g) / delta + 4)
                
                # Apply hue rotation
                h = (h + hue_rotation) % 360
                
                # Calculate saturation
                s = 0 if cmax == 0 else delta / cmax
                
                # Apply saturation scaling
                s = s * sat_factor
                s = max(0, min(1, s))  # Clamp to [0,1]
                
                # Calculate value
                v = cmax
                
                # Convert HSV back to RGB
                c = v * s
                x = c * (1 - abs((h / 60) % 2 - 1))
                m = v - c
                
                if 0 <= h < 60:
                    r, g, b = c, x, 0
                elif 60 <= h < 120:
                    r, g, b = x, c, 0
                elif 120 <= h < 180:
                    r, g, b = 0, c, x
                elif 180 <= h < 240:
                    r, g, b = 0, x, c
                elif 240 <= h < 300:
                    r, g, b = x, 0, c
                else:
                    r, g, b = c, 0, x
                
                r, g, b = (r + m) * 255, (g + m) * 255, (b + m) * 255
                
                # Apply RGB multipliers
                r = r * self.r_scale
                g = g * self.g_scale
                b = b * self.b_scale
                
                # Clamp values to [0, 255]
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                
                # Update the pixel
                img_copy[i, j][0] = r
                img_copy[i, j][1] = g
                img_copy[i, j][2] = b
        
        return img_copy

    def _simulate_dry_run(self):
        """Simulate processing for dry run mode."""
        output_dir = self.create_output_directory()
        variations_count = self.sat_count * self.hue_count
        
        logger.info(f"DRY RUN: Would generate {variations_count} variations")
        logger.info(f"DRY RUN: Would save to directory: {output_dir}")
        
        for i in range(variations_count):
            sat_idx = i // self.hue_count
            hue_idx = i % self.hue_count
            sat_factor = (sat_idx + 1) / self.sat_count
            hue_rotation = (hue_idx * 360) / self.hue_count
            
            logger.info(f"DRY RUN: Variation {i+1}: "
                        f"Saturation={sat_factor:.2f}, "
                        f"Hue Rotation={hue_rotation:.1f}°")
    
    def _save_processing_details(self, output_dir):
        """Save processing details to a log file in the output directory."""
        if not self.log_file:
            return
        
        details = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input_image": str(self.input_path),
            "output_directory": str(output_dir),
            "parameters": {
                "saturation_count": self.sat_count,
                "hue_count": self.hue_count,
                "rgb_multipliers": {
                    "r": self.r_scale,
                    "g": self.g_scale,
                    "b": self.b_scale
                },
                "skip_gray": self.skip_gray,
                "skip_near_gray_threshold": self.skip_near_gray_threshold,
                "transparent_only": self.transparent_only,
                "opaque_only": self.opaque_only
            },
            "total_variations": self.sat_count * self.hue_count
        }
        
        with open(output_dir / "processing_details.json", "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2, ensure_ascii=False)


def load_config_file(config_path):
    """
    Load configuration from a JSON or YAML file.
    
    Args:
        config_path (str): Path to the configuration file
    
    Returns:
        dict: Configuration parameters or None if loading failed
    """
    try:
        config_path = Path(config_path)
        
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            else:  # Assume JSON
                config = json.load(f)
        
        if not isinstance(config, dict):
            logger.error(f"Invalid config format in {config_path}")
            return None
            
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        return None


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate color variations of an image by adjusting hue and saturation.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        'input_path',
        type=str,
        help='Path to the input image file (PNG, JPG, or JPEG)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory (default: same as input image folder)'
    )
    
    parser.add_argument(
        '--saturation-count', '-s',
        type=int,
        default=3,
        help='Number of saturation levels'
    )
    
    parser.add_argument(
        '--hue-count', '-u',
        type=int,
        default=10,
        help='Number of hue steps'
    )
    
    parser.add_argument(
        '--r-scale',
        type=float,
        default=1.0,
        help='Red channel multiplier'
    )
    
    parser.add_argument(
        '--g-scale',
        type=float,
        default=1.0,
        help='Green channel multiplier'
    )
    
    parser.add_argument(
        '--b-scale',
        type=float,
        default=1.0,
        help='Blue channel multiplier'
    )
    
    parser.add_argument(
        '--skip-gray',
        action='store_true',
        help='Skip pixels where R=G=B (exact grayscale)'
    )
    
    parser.add_argument(
        '--skip-near-gray',
        type=int,
        default=0,
        dest='skip_near_gray_threshold',
        help='Skip pixels where max(R,G,B) - min(R,G,B) < threshold'
    )
    
    parser.add_argument(
        '--transparent-only',
        action='store_true',
        help='Process only transparent pixels (if alpha channel exists)'
    )
    
    parser.add_argument(
        '--opaque-only',
        action='store_true',
        help='Process only opaque pixels (if alpha channel exists)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (JSON or YAML)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Simulate processing without generating images'
    )
    
    parser.add_argument(
        '--log-file', '-l',
        type=str,
        help='Path to log file'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Check if input file exists
    if not os.path.isfile(args.input_path):
        logger.error(f"Input file not found: {args.input_path}")
        return 1
    
    # Load configuration
    if args.config:
        config = load_config_file(args.config)
        if not config:
            return 1
    else:
        # Use command line arguments
        config = vars(args)
    
    # Initialize processor and process the image
    processor = ImageProcessor(config)
    success = processor.process_image()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())