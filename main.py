import requests
from bs4 import BeautifulSoup
import os
import time
from datetime import datetime, timezone
import re
from threading import Event
from urllib.parse import urlparse

stop_flag = Event()


def download_article(article_url, article_folder, output_file, stop_flag):
    try:
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()  # Проверка на ошибки HTTP
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Извлекаем дату и время публикации статьи
            date_element = soup.find('time', class_='article__header__date')
            date_published = date_element['datetime']

            # Преобразуем дату публикации в объект datetime
            date_published = datetime.fromisoformat(date_published).replace(tzinfo=timezone.utc)

            # Генерируем уникальный идентификатор на основе даты публикации
            article_id = date_published.strftime("%Y-%m-%d_%H-%M-%S")

            # Проверяем, если статья с таким идентификатором уже существует в файле
            if article_id in open(output_file, 'r', encoding='utf-8').read():
                print(f"Статья {article_url} с датой {article_id} уже добавлена.")
                return False

            # Получаем текст статьи
            article_text = "\n".join([p.get_text() for p in soup.find_all('p')])

            # Очищаем текст от лишних пробелов и отступов с помощью регулярных выражений
            article_text = re.sub(r'\s+', ' ', article_text)
            article_text = article_text.strip()

            # Проверяем, если статья старше указанного максимального возраста
            current_time = datetime.now(timezone.utc)
            time_difference = current_time - date_published

            if time_difference.total_seconds() > max_age_hours * 3600:
                print(f"Статья {article_url} была опубликована более чем {max_age_hours} часов назад. Пропускаем.")
                stop_flag.set()
                return False

            # Открываем файл в режиме "дополнение" и записываем новую статью
            with open(output_file, 'a', encoding='utf-8') as file:
                file.write(f"Начало статьи ({article_id}):\n")
                file.write(article_text + '\n')
                file.write("----------------------------\n")
            print(f"+1 element date = {article_id}")
            return True
        else:
            print(f"Не удалось получить доступ к статье {article_url}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Произошла ошибка при запросе: {e}")
        return False


# URL страницы, на которой находятся разные статьи
page_url = 'https://www.rbc.ru/politics/'  # Замените на URL конкретной страницы

page_urls = [
    'https://www.rbc.ru/economics/',
    'https://www.rbc.ru/finances/',
    'https://www.rbc.ru/politics/'
]

# Папка, в которой будут сохраняться статьи
article_folder = 'articles'

# Имя файла, в который будут добавляться статьи
output_file = 'all_articles.txt'

# Создаем папку, если она не существует
os.makedirs(article_folder, exist_ok=True)

# Если файл не существует, создаем его
if not os.path.isfile(output_file):
    with open(output_file, 'w', encoding='utf-8'):
        pass

# Список для хранения загруженных дат
downloaded_dates = []

# Интервал времени в часах между сканированиями
interval_hours = 0.1

# Актуальность статьи в часах
max_age_hours = 12

# Отправляем GET-запрос и получаем содержимое страницы
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

while True:
    for page_url in page_urls:
        url_parts = urlparse(page_url)
        url_parts = page_url.split('/')
        domain = url_parts[-2]
        file_name = f"{domain}.txt"
        output_file = os.path.join(article_folder, file_name)

        # Создаем файл, если его не существует
        if not os.path.isfile(output_file):
            with open(output_file, 'w', encoding='utf-8'):
                pass

        try:
            response = requests.get(page_url, headers=headers)
            response.raise_for_status()  # Проверка на ошибки HTTP
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Находим все элементы <meta> с атрибутом itemprop="url"
                meta_elements = soup.find_all('meta', itemprop="url")

                for meta_element in meta_elements:
                    article_url = meta_element['content']

                    if not download_article(article_url, article_folder, output_file, Event()):
                        print("Остановка парсинга старых статей.")
                        break  # Если download_article возвращает False, прерываем обработку текущей статьи

                # Спим в течение указанного интервала времени
                 # Переводим часы в секунды
            else:
                print("Не удалось получить доступ к странице с новостями.")
        except requests.exceptions.RequestException as e:
            print(f"Произошла ошибка при запросе: {e}")

    time.sleep(interval_hours * 3600)
