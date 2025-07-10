import time
import random
from dataclasses import asdict

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from yandex_reviews_parser.helpers import ParserHelper
from yandex_reviews_parser.storage import Review, Info

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Parser:
    def __init__(self, driver):
        self.driver = driver

    def __scroll_to_bottom(self, elem) -> None:
        """
        Скроллим список до последнего отзыва
        :param elem: Последний отзыв в списке
        :param driver: Драйвер undetected_chromedriver
        :return: None
        """
        self.driver.execute_script(
            "arguments[0].scrollIntoView();",
            elem
        )
        time.sleep(1)
        new_elem = self.driver.find_elements(By.CLASS_NAME, "business-reviews-card-view__review")[-1]
        if elem == new_elem:
            return
        self.__scroll_to_bottom(new_elem)

    def __get_data_item(self, elem):
        """
        Спарсить данные по отзыву
        :param elem: Отзыв из списка
        :return: Словарь
        {
            name: str
            icon_href: Union[str, None]
            date: float
            text: str
            stars: float
        }
        """
        try:
            name = elem.find_element(By.XPATH, ".//span[@itemprop='name']").text
        except NoSuchElementException:
            name = None

        try:
            icon_href = elem.find_element(By.XPATH, ".//div[@class='user-icon-view__icon']").get_attribute('style')
            icon_href = icon_href.split('"')[1]
        except NoSuchElementException:
            icon_href = None

        try:
            date = elem.find_element(By.XPATH, ".//meta[@itemprop='datePublished']").get_attribute('content')
        except NoSuchElementException:
            date = None

        try:
            text = elem.find_element(By.CSS_SELECTOR, "span.spoiler-view__text-container").text
        except NoSuchElementException:
            text = None
        try:
            stars = elem.find_elements(By.XPATH, ".//div[@class='business-rating-badge-view__stars _spacing_normal']/span")
            stars = ParserHelper.get_count_star(stars)
        except NoSuchElementException:
            stars = 0

        try:
            # Check if expand button exists
            expand_button = elem.find_element(By.CLASS_NAME, "business-review-view__comment-expand")
            if expand_button:
                # Click using JavaScript to avoid direct interaction
                self.driver.execute_script("arguments[0].click()", expand_button)
                # Wait briefly for DOM update
                time.sleep(0.1)
                # Refind the answer bubble with stale-safe approach
                try:
                    answer = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".business-review-comment-content__bubble")
                        )
                    ).text
                except (NoSuchElementException, TimeoutException):
                    answer = None
            else:
                answer = None
        except NoSuchElementException:
            answer = None

        item = Review(
            name=name,
            icon_href=icon_href,
            date=ParserHelper.form_date(date),
            text=text,
            stars=stars,
            answer=answer
        )
        return asdict(item)

    def __get_data_campaign(self) -> dict:
        """
        Получаем данные по компании.
        :return: Словарь данных
        {
            name: str
            rating: float
            count_rating: int
            stars: float
        }
        """
        try:
            xpath_name = ".//h1[@class='orgpage-header-view__header']"
            name = self.driver.find_element(By.XPATH, xpath_name).text
        except NoSuchElementException:
            name = None
        try:
            xpath_rating_block = ".//div[@class='business-summary-rating-badge-view__rating-and-stars']"
            rating_block = self.driver.find_element(By.XPATH, xpath_rating_block)
            xpath_rating = ".//div[@class='business-summary-rating-badge-view__rating']/span[contains(@class, 'business-summary-rating-badge-view__rating-text')]"
            rating = rating_block.find_elements(By.XPATH, xpath_rating)
            rating = ParserHelper.format_rating(rating)
            xpath_count_rating = ".//div[@class='business-summary-rating-badge-view__rating-count']/span[@class='business-rating-amount-view _summary']"
            count_rating_list = rating_block.find_element(By.XPATH, xpath_count_rating).text
            count_rating = ParserHelper.list_to_num(count_rating_list)
            xpath_stars = ".//div[@class='business-rating-badge-view__stars _spacing_normal']/span"
            stars = ParserHelper.get_count_star(rating_block.find_elements(By.XPATH, xpath_stars))
        except NoSuchElementException:
            rating = 0
            count_rating = 0
            stars = 0

        item = Info(
            name=name,
            rating=rating,
            count_rating=count_rating,
            stars=stars
        )
        return asdict(item)

    def __get_review_by_position(self, position):
        """Locate a review by its aria-posinset value"""
        try:
            return WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f".business-reviews-card-view__review[aria-posinset='{position}']")
                )
            )
        except TimeoutException:
            return None

    def __ensure_all_reviews_expanded(self):
        """Ensure all reviews are expanded using stable position identifiers"""
        # Get all review positions
        position_elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".business-reviews-card-view__review[aria-posinset]"
        )

        if not position_elements:
            return

        # Extract positions
        positions = [int(el.get_attribute("aria-posinset")) for el in position_elements]
        total_reviews = max(positions) if positions else 0

        # Get viewport dimensions
        viewport_height = self.driver.execute_script("return window.innerHeight;")

        for pos in range(1, total_reviews + 1):
            try:
                # Get fresh reference using position
                review = self.__get_review_by_position(pos)
                if not review:
                    continue

                # Check if expansion is needed
                try:
                    expand_btn = review.find_element(
                        By.CSS_SELECTOR,
                        ".business-review-view__expand"
                    )
                except NoSuchElementException:
                    continue  # Already expanded

                # Scroll to position if needed
                review_y = review.location['y']
                current_scroll = self.driver.execute_script("return window.pageYOffset;")

                if not (current_scroll <= review_y < current_scroll + viewport_height):
                    # Scroll to position with offset
                    scroll_target = max(0, review_y - viewport_height//3)
                    self.driver.execute_script(
                        f"window.scrollTo({{top: {scroll_target}, behavior: 'smooth'}});"
                    )
                    time.sleep(random.uniform(0.3, 0.6))

                # Expand the review
                self.driver.execute_script("arguments[0].click()", expand_btn)

                # Random delay between actions
                time.sleep(random.uniform(0.1, 0.3))

                # Occasionally scroll randomly to mimic human
                if random.random() > 0.8:  # 20% chance
                    random_scroll = random.randint(-100, 100)
                    self.driver.execute_script(
                        f"window.scrollBy(0, {random_scroll});"
                    )
                    time.sleep(random.uniform(0.2, 0.4))

            except Exception as e:
                print(f"Error expanding review {pos}: {str(e)}")
                continue

    def __get_data_reviews(self) -> list:
        # Scroll to load all reviews
        elements = self.driver.find_elements(By.CLASS_NAME, "business-reviews-card-view__review")
        if len(elements) > 1:
            self.__scroll_to_bottom(elements[-1])

        # Ensure ALL reviews are expanded using stable positions
        self.__ensure_all_reviews_expanded()

        # Get fresh references for all reviews using positions
        reviews = []
        position_elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".business-reviews-card-view__review[aria-posinset]"
        )
        positions = sorted([int(el.get_attribute("aria-posinset")) for el in position_elements])

        for pos in positions:
            review = self.__get_review_by_position(pos)
            if review:
                reviews.append(self.__get_data_item(review))

        return reviews

    def __isinstance_page(self):
        try:
            xpath_name = ".//h1[@class='orgpage-header-view__header']"
            name = self.driver.find_element(By.XPATH, xpath_name).text
            return True
        except NoSuchElementException:
            return False

    def parse_all_data(self) -> dict:
        """
        Начинаем парсить данные.
        :return: Словарь данных
        {
             company_info:{
                    name: str
                    rating: float
                    count_rating: int
                    stars: float
            },
            company_reviews:[
                {
                  name: str
                  icon_href: str
                  date: timestamp
                  text: str
                  stars: float
                }
            ]
        }
        """
        if not self.__isinstance_page():
            return {'error': 'Страница не найдена'}
        return {'company_info': self.__get_data_campaign(), 'company_reviews': self.__get_data_reviews()}

    def parse_reviews(self) -> dict:
        """
        Начинаем парсить данные только отзывы.
        :return: Массив отзывов
        {
            company_reviews:[
                {
                  name: str
                  icon_href: str
                  date: timestamp
                  text: str
                  stars: float
                }
            ]
        }

        """
        if not self.__isinstance_page():
            return {'error': 'Страница не найдена'}
        return {'company_reviews': self.__get_data_reviews()}

    def parse_company_info(self) -> dict:
        """
        Начинаем парсить данные только данные о компании.
        :return: Объект компании
        {
            company_info:
                {
                    name: str
                    rating: float
                    count_rating: int
                    stars: float
                }
        }
        """
        if not self.__isinstance_page():
            return {'error': 'Страница не найдена'}
        return {'company_info': self.__get_data_campaign()}
