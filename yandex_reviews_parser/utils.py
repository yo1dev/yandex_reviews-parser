import random
import time
import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from yandex_reviews_parser.parsers import Parser
from yandex_reviews_parser.user_agents import user_agents

class YandexParser:
    def __init__(self, max_pages_per_session=8):
        self.driver = None
        self.session_use_count = 0
        self.max_pages_per_session = max_pages_per_session
        self.user_agents = user_agents

    def create_driver(self):
        """Create a new driver instance with randomized fingerprint"""
        opts = uc.ChromeOptions()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('headless')
        opts.add_argument('--disable-gpu')
        opts.add_argument(f'--user-agent={random.choice(self.user_agents)}')

        # Randomize viewport size
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        opts.add_argument(f'--window-size={width},{height}')

        return uc.Chrome(
            options=opts
        )

    def rotate_session(self):
        """Rotate to a new browser session"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

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

            # Random scroll to simulate reading
            if random.random() > 0.4:  # 60% chance
                scroll_pixels = random.randint(200, 800)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_pixels})")
                time.sleep(random.uniform(0.3, 0.8))

            # Initialize the original Parser class
            parser = Parser(self.driver)
            time.sleep(2 + random.random()) # Allow page to settle

            # Parse company info first to detect blocks
            company_info = parser.parse_company_info().get('company_info', {})

            # Check for potential block
            if not company_info.get('name'):
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
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
