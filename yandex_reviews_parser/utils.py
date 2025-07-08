import shutil
import tempfile
import random
import time
import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from yandex_reviews_parser.parsers import Parser

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class YandexParser:
    def __init__(self, max_pages_per_session: int = 8):
        self.driver = None
        self.session_use_count = 0
        self.max_pages_per_session = max_pages_per_session
        self.user_data_dir = None

    def create_driver(self):
        """Create a new driver instance with randomized fingerprint"""
        opts = uc.ChromeOptions()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1200,800')

        opts.add_argument('--disable-blink-features=AutomationControlled')

        opts.add_argument("--disable-web-security")
        opts.add_argument("--disable-site-isolation-trials")
        opts.add_argument("--disable-features=SitePerProcess")

        self.user_data_dir = tempfile.mkdtemp()
        opts.add_argument(f"--user-data-dir={self.user_data_dir}")
        opts.add_argument("--profile-directory=Default") 

        return uc.Chrome(
            headless=True,
            options = opts
        )

    def rotate_session(self):
        """Rotate to a new browser session"""
        self.close()

        self.driver = self.create_driver()
        self.session_use_count = 0
        time.sleep(random.uniform(1.0, 2.0))

    def parse_company(self, id_yandex: int):
        """Parse a company with anti-detection measures"""
        # Rotate session if needed
        if not self.driver or self.session_use_count >= self.max_pages_per_session:
            self.rotate_session()

        try:
            # Simulate human behavior
            time.sleep(random.uniform(0.3, 1.2)) # Variable think time

            # Navigate to target
            url = f'https://yandex.ru/maps/org/{id_yandex}/reviews/'
            self.driver.get(url)

            # Wait for critical element instead of fixed sleep
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "orgpage-header-view__header"))
            )

            # Initialize the original Parser class
            parser = Parser(self.driver)
            time.sleep(2 + random.random()) # Allow page to settle

            # Parse company info first to detect blocks
            company_info = parser.parse_company_info().get('company_info', {})

            # Check for potential block
            if not company_info.get('name'):
                time.sleep(random.uniform(5, 15))
                # Rotate and retry once
                self.rotate_session()
                self.driver.get(url)
                time.sleep(3)
                parser = Parser(self.driver)
                company_info = parser.parse_company_info().get('company_info', {})

                if not company_info.get('name'):
                    return {'error': 'Possible block detected'}

            # Parse reviews only if company info is valid
            reviews = parser.parse_reviews().get('company_reviews', [])

            self.session_use_count += 1
            return {
                'company_info': company_info,
                'company_reviews': reviews
            }

        except WebDriverException as e:
            # Rotate session on browser errors
            self.rotate_session()
            return {'error': f'Browser error: {str(e)}'}

        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}

    def close(self):
        """Clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

        if self.user_data_dir:
            # Retry removal with increasing delays
            for _ in range(5):  # Try up to 5 times
                try:
                    shutil.rmtree(self.user_data_dir)
                    break  # Exit loop if successful
                except OSError:
                    time.sleep(0.5)  # Wait before retrying
            self.user_data_dir = None  # Reset regardless of success
