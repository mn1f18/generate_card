from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
from .card_extractor import extract_card_from_image

def html_to_image(html_path, output_path, width=393, height=None):
    """
    Renders HTML file to an image using Selenium and Chrome, emulating a mobile device.
    
    Parameters:
        html_path: Path to HTML file or URL
        output_path: Path to save the output image
        width: Width of the viewport in pixels (default: 393px - iPhone 15 width)
        height: Height of the viewport in pixels (None for auto, dynamically calculated)
    """
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    # Remove specific window size and user agent as mobile emulation handles this
    # chrome_options.add_argument(f"--window-size={width},{height or 852}")
    # chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--force-device-scale-factor=2") # Keep high DPI

    # Define mobile emulation settings for iPhone 15
    mobile_emulation = {
        "deviceMetrics": {
            "width": width,
            "height": height or 852,  # Use a default height if not dynamic
            "pixelRatio": 3.0 # iPhone 15 has a 3x pixel ratio
        },
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    try:
        # Initialize the driver with mobile emulation options
        driver = webdriver.Chrome(options=chrome_options)
        
        # Convert to absolute path if it's a local file
        if not html_path.startswith('http'):
            html_path = 'file://' + os.path.abspath(html_path)
        
        # Load the page
        driver.get(html_path)
        
        # Wait for page rendering and any JavaScript execution
        time.sleep(2)
        
        # Dynamically calculate height if needed
        if height is None:
            # Calculate the full page height
            calculated_height = driver.execute_script("""
                return Math.max(
                    document.body.scrollHeight, 
                    document.documentElement.scrollHeight,
                    document.body.offsetHeight, 
                    document.documentElement.offsetHeight,
                    document.body.clientHeight,
                    document.documentElement.clientHeight
                );
            """)
            print(f"自适应内容高度: {calculated_height}像素")
            
            # Update mobile emulation height and re-initialize driver for correct height
            # Note: Re-initializing is necessary because mobileEmulation height is set at launch
            driver.quit() # Close the current driver
            mobile_emulation["deviceMetrics"]["height"] = calculated_height
            chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
            driver = webdriver.Chrome(options=chrome_options) # Re-launch with correct height
            driver.get(html_path) # Reload page
            time.sleep(1) # Wait for reload

        # Capture screenshot
        driver.save_screenshot(output_path)
        print(f"Image saved to {output_path}")
        return True
    
    except Exception as e:
        print(f"Error converting HTML to image: {e}")
        return False
    
    finally:
        if 'driver' in locals():
            driver.quit()

# Only run example code when this file is executed directly, not when imported
if __name__ == "__main__":
    # Example usage
    html_to_image('./96a32822-aebe-4f5a-a2c6-2bed830af5f9.html', 'output.png')
    # Uncommenting the below line will run the card extraction too
    extract_card_from_image('output.png', 'card.png')