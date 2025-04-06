import cv2
import numpy as np
from pdf2image import convert_from_path
import os
from PIL import Image
from card_extractor import extract_card_from_image  # 导入从单独文件中拆分出的函数
import concurrent.futures
import time # For timing comparisons

# Define a helper function to check if a row is white
def is_white_row(row, threshold=245):
    """Checks if a row in an image is predominantly white."""
    # If the row's mean color value is higher than the threshold, consider it white.
    # Using np.all might be faster if strict white is expected, but mean is robust to noise.
    return np.mean(row) > threshold

# Define the image processing logic for a single page
def process_page_image(args):
    """Processes a single page image: scales (optional), removes borders."""
    i, img_pil, total_pages, scale_factor = args
    try:
        # Convert PIL Image to NumPy array for processing
        img_np = np.array(img_pil)

        # --- Optional Scaling (kept scale_factor=1 as per original code) ---
        if scale_factor != 1:
            try:
                # print(f"Applying {scale_factor}x linear interpolation scaling to page {i+1}...") # Can be verbose
                h, w = img_np.shape[:2]
                new_h, new_w = int(h * scale_factor), int(w * scale_factor)
                img_np = cv2.resize(img_np, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                # print(f"Scaling complete for page {i+1}.")
            except Exception as scale_error:
                print(f"\nWarning: Scaling failed for page {i+1} ({scale_error}). Using original resolution.")
        # --- End Scaling ---

        # Find the top border (skip for the first page)
        top_crop = 0
        if i > 0: # Only crop top if not the first page
            for y in range(img_np.shape[0]):
                if not is_white_row(img_np[y]):
                    top_crop = y
                    break
            # Add a small safety margin if needed, e.g., top_crop = max(0, top_crop - 2)

        # Find the bottom border (skip for the last page)
        bottom_crop = img_np.shape[0]
        if i < total_pages - 1: # Only crop bottom if not the last page
            for y in range(img_np.shape[0] - 1, top_crop -1, -1): # Search down to top_crop
                 if not is_white_row(img_np[y]):
                    bottom_crop = y + 1 # Crop below the last content row
                    break
            # Add a small safety margin if needed, e.g., bottom_crop = min(img_np.shape[0], bottom_crop + 2)


        # Crop the image
        # print(f"Page {i+1}: Original Shape: {img_np.shape}, Cropping: top={top_crop}, bottom={bottom_crop}") # Debugging info
        if top_crop >= bottom_crop:
             print(f"Warning: Page {i+1} cropping resulted in empty image (top={top_crop}, bottom={bottom_crop}). Skipping crop.")
             cropped_img_np = img_np # Keep original if crop is invalid
        else:
            cropped_img_np = img_np[top_crop:bottom_crop]
            # print(f"Page {i+1}: Cropped Shape: {cropped_img_np.shape}") # Debugging info

        # Return index and processed NumPy array (avoids PIL conversion overhead here)
        return i, cropped_img_np

    except Exception as e:
        print(f"Error processing page {i+1}: {e}")
        # Return original image data if processing fails
        return i, np.array(img_pil)


def pdf_to_images_optimized(pdf_path, output_folder, dpi=1000):
    """
    Converts PDF pages to a single vertically stitched image, removing borders between pages.
    Optimized for speed using parallel processing.

    Args:
        pdf_path (str): Path to the PDF file.
        output_folder (str): Folder to save the output image.
        dpi (int): Resolution for PDF conversion. IMPORTANT: Higher DPI significantly impacts
                   performance and memory. 300 is often sufficient, 1000 is very high.
                   Consider lowering this value (e.g., 150-300) for speed. Default is 1000 for compatibility.

    Returns:
        str: Path to the combined image, or None if conversion fails.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        start_time = time.time()
        print(f"Starting PDF conversion (DPI={dpi})...")
        # Use thread_count for potential speedup in pdf2image/poppler
        # Use more threads if your system can handle it (e.g., os.cpu_count())
        images_pil = convert_from_path(pdf_path, dpi=dpi, thread_count=4) # Adjust thread_count as needed
        conversion_time = time.time() - start_time
        print(f"PDF conversion finished in {conversion_time:.2f} seconds, got {len(images_pil)} pages.")

        if not images_pil:
            print("No images were generated from the PDF.")
            return None

        processed_results = {}
        total_pages = len(images_pil)
        scale_factor = 1 # Keep scale factor as 1 as per original requirement

        print("Starting parallel image processing...")
        start_processing_time = time.time()
        # Use ThreadPoolExecutor for parallel processing of pages
        # Adjust max_workers based on your CPU cores
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            # Prepare arguments for each task
            tasks_args = [(i, images_pil[i], total_pages, scale_factor) for i in range(total_pages)]
            # Map the processing function to the arguments
            futures = {executor.submit(process_page_image, arg): i for i, arg in enumerate(tasks_args)}

            for future in concurrent.futures.as_completed(futures):
                original_index = futures[future]
                try:
                    # Get the result (index, processed_image_np)
                    idx, processed_image_np = future.result()
                    processed_results[idx] = processed_image_np # Store with original index
                    print(f"  Processed page {idx + 1}/{total_pages}")
                except Exception as exc:
                    print(f'Page {original_index + 1} generated an exception: {exc}')
                    # Optionally handle failure, e.g., use original image
                    processed_results[original_index] = np.array(images_pil[original_index])


        processing_time = time.time() - start_processing_time
        print(f"Parallel image processing finished in {processing_time:.2f} seconds.")

        # Ensure results are sorted by original page order
        sorted_processed_images_np = [processed_results[i] for i in range(total_pages) if i in processed_results]

        if not sorted_processed_images_np:
             print("Image processing failed for all pages.")
             return None

        # Calculate final image dimensions from NumPy arrays
        widths = [img_np.shape[1] for img_np in sorted_processed_images_np]
        heights = [img_np.shape[0] for img_np in sorted_processed_images_np]
        max_width = max(widths) if widths else 0
        total_height = sum(heights) if heights else 0

        if max_width == 0 or total_height == 0:
            print("Calculated final image dimensions are zero. Cannot proceed.")
            return None

        print(f"Creating final combined image (Width: {max_width}, Height: {total_height})...")
        start_combining_time = time.time()

        # Create the combined image using PIL
        # Ensure 3 channels (RGB) for the final image. Find the mode from the first valid image.
        output_mode = 'RGB'
        if sorted_processed_images_np[0].ndim == 3:
            channels = sorted_processed_images_np[0].shape[2]
            if channels == 4:
                output_mode = 'RGBA' # Keep alpha if present
            elif channels == 1:
                 output_mode = 'L' # Grayscale
        elif sorted_processed_images_np[0].ndim == 2:
             output_mode = 'L' # Grayscale

        # If any image has color, default to RGB
        for img_np in sorted_processed_images_np:
             if img_np.ndim == 3 and img_np.shape[2] == 3:
                 output_mode = 'RGB'
                 break
             if img_np.ndim == 3 and img_np.shape[2] == 4:
                 output_mode = 'RGBA' # Prioritize RGBA if found
                 # Don't break yet, check if others force RGB

        # If ended up with RGBA but some images are RGB/L, convert final to RGB
        # Or handle mixing modes more carefully if alpha is critical. Sticking to RGB is safer.
        # Let's force RGB for simplicity unless alpha was explicitly detected and consistent.
        final_mode = 'RGB' if output_mode != 'L' else 'L' # Stick to RGB or L


        # Create blank canvas. Default background to white.
        combined_image = Image.new(final_mode, (max_width, total_height), color='white')

        current_y = 0
        for img_np in sorted_processed_images_np:
            # Convert NumPy array back to PIL Image for pasting
            img_pil_to_paste = Image.fromarray(img_np)

            # Ensure image matches the final combined image mode before pasting
            if img_pil_to_paste.mode != combined_image.mode:
                img_pil_to_paste = img_pil_to_paste.convert(combined_image.mode)

            # Center image if its width is less than max_width (optional, original didn't do this)
            paste_x = (max_width - img_pil_to_paste.width) // 2
            combined_image.paste(img_pil_to_paste, (paste_x, current_y))
            current_y += img_pil_to_paste.height # Use the actual height of the pasted image

        combining_time = time.time() - start_combining_time
        print(f"Image combination finished in {combining_time:.2f} seconds.")

        # Save the combined image
        pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        combined_image_path = os.path.join(output_folder, f'{pdf_filename}_combined_optimized.png')
        combined_image.save(combined_image_path, 'PNG')
        total_time = time.time() - start_time
        print(f"Optimized processing complete. Total time: {total_time:.2f} seconds.")
        print(f"Combined image saved to: {combined_image_path}")

        return combined_image_path

    except Exception as e:
        import traceback
        print(f"Error in optimized PDF to combined image conversion: {e}")
        traceback.print_exc() # Print detailed traceback
        return None

# --- Main execution block remains the same, but calls the optimized function ---
if __name__ == "__main__":
    # 1. Convert PDF to combined image using the optimized function
    pdf_path = "./output_weasyprint.pdf" # Ensure this PDF exists
    output_folder = "output_images_optimized"
    # CRITICAL: Test with a more reasonable DPI first, e.g., 300
    # image_path = pdf_to_images_optimized(pdf_path, output_folder, dpi=300)
    image_path = pdf_to_images_optimized(pdf_path, output_folder, dpi=300) # Using 300 based on original example call

    # 2. Extract card from the combined image (if successful)
    if image_path:
        card_output_path = os.path.join(output_folder, 'card_extracted.png')
        print(f"\nExtracting card from: {image_path}")
        try:
            extract_card_from_image(
                image_path,
                card_output_path,
                min_area=500,  # Adjust as needed
                debug=True     # Enable debug if needed for extraction visualization
            )
            print(f"Card extraction attempted. Output expected at: {card_output_path}")
        except Exception as extract_error:
            print(f"Error during card extraction: {extract_error}")
    else:
        print("\nPDF conversion failed, skipping card extraction.")